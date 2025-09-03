"""Main CLI application for VTT Summarizer."""

import click
import json
import sys
from pathlib import Path
from typing import Optional
import logging

from .config import Config
from .summarizer import VTTSummarizer


@click.group()
@click.option('--config', '-c', 
              type=click.Path(exists=True, path_type=Path),
              help='Path to configuration YAML file')
@click.option('--verbose', '-v', is_flag=True, 
              help='Enable verbose logging')
@click.pass_context
def cli(ctx, config: Optional[Path], verbose: bool):
    """VTT Summarizer - Generate meeting summaries from VTT files using AWS Bedrock."""
    ctx.ensure_object(dict)
    
    try:
        # Load configuration
        if config:
            ctx.obj['config'] = Config(str(config))
        else:
            ctx.obj['config'] = Config()
        
        # Override logging level if verbose
        if verbose:
            ctx.obj['config']._config['logging']['level'] = 'DEBUG'
        
        ctx.obj['verbose'] = verbose
        
    except Exception as e:
        click.echo(f"Error loading configuration: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--force', '-f', is_flag=True,
              help='Force overwrite existing summary files')
@click.option('--output-format', type=click.Choice(['json', 'text']),
              default='text', help='Output format for results')
@click.pass_context
def process(ctx, force: bool, output_format: str):
    """Process all VTT files in the walkthroughs directory."""
    config = ctx.obj['config']
    
    try:
        summarizer = VTTSummarizer(config)
        
        click.echo("🚀 Starting VTT processing...")
        click.echo(f"📁 Input folder: {config.input_folder}")
        click.echo(f"🤖 Using model: {config.bedrock_model_id}")
        click.echo()
        
        # Process all walkthroughs
        results = summarizer.process_all_walkthroughs()
        
        # Override force_overwrite if needed
        if force:
            click.echo("🔄 Force mode enabled - will overwrite existing summaries")
            # Re-process with force flag
            for result in results['results']:
                if result['status'] == 'skipped':
                    folder_path = Path(config.input_folder) / result['folder']
                    vtt_files = list(folder_path.glob("*.vtt"))
                    if vtt_files:
                        new_result = summarizer.process_single_walkthrough(
                            folder_path, vtt_files[0], force_overwrite=True
                        )
                        # Update the result
                        result.update(new_result)
                        if new_result['status'] == 'success':
                            results['processed'] += 1
                            results['skipped'] -= 1
        
        # Output results
        if output_format == 'json':
            click.echo(json.dumps(results, indent=2))
        else:
            _display_text_results(results)
            
    except KeyboardInterrupt:
        click.echo("\\n❌ Processing interrupted by user", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error during processing: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('folder_name')
@click.option('--force', '-f', is_flag=True,
              help='Force overwrite existing summary file')
@click.pass_context
def process_single(ctx, folder_name: str, force: bool):
    """Process a single walkthrough folder by name."""
    config = ctx.obj['config']
    
    try:
        folder_path = Path(config.input_folder) / folder_name
        
        if not folder_path.exists():
            click.echo(f"❌ Folder not found: {folder_path}", err=True)
            sys.exit(1)
        
        # Find VTT file in folder
        vtt_files = list(folder_path.glob("*.vtt"))
        if not vtt_files:
            click.echo(f"❌ No VTT file found in {folder_name}", err=True)
            sys.exit(1)
        
        vtt_file = vtt_files[0]
        
        summarizer = VTTSummarizer(config)
        
        click.echo(f"🚀 Processing: {folder_name}")
        click.echo(f"📄 VTT file: {vtt_file.name}")
        click.echo()
        
        result = summarizer.process_single_walkthrough(folder_path, vtt_file, force)
        
        if result['status'] == 'success':
            click.echo("✅ Summary generated successfully!")
            click.echo(f"📝 Saved to: {result['summary_path']}")
            if 'processing_time' in result:
                click.echo(f"⏱️  Processing time: {result['processing_time']['total_time']}s")
        elif result['status'] == 'skipped':
            click.echo("⏭️  Summary already exists (use --force to overwrite)")
        else:
            click.echo(f"❌ Processing failed: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def test(ctx):
    """Test AWS Bedrock connection and configuration."""
    config = ctx.obj['config']
    
    try:
        from .bedrock_client import BedrockClient
        
        click.echo("🧪 Testing VTT Summarizer setup...")
        click.echo()
        
        # Test configuration
        click.echo("📋 Configuration:")
        click.echo(f"  - AWS Region: {config.aws_region}")
        click.echo(f"  - Bedrock Model: {config.bedrock_model_id}")
        click.echo(f"  - Input Folder: {config.input_folder}")
        click.echo(f"  - Max Tokens: {config.bedrock_max_tokens}")
        click.echo()
        
        # Test input folder
        input_path = Path(config.input_folder)
        if input_path.exists():
            vtt_count = len(list(input_path.glob("*/*.vtt")))
            click.echo(f"✅ Input folder exists with {vtt_count} VTT files")
        else:
            click.echo(f"❌ Input folder not found: {input_path}", err=True)
            return
        
        # Test Bedrock connection
        click.echo("🔗 Testing AWS Bedrock connection...")
        bedrock_client = BedrockClient(config)
        
        if bedrock_client.test_connection():
            click.echo("✅ Bedrock connection successful!")
        else:
            click.echo("❌ Bedrock connection failed!", err=True)
            return
        
        click.echo()
        click.echo("🎉 All tests passed! Ready to process VTT files.")
        
    except Exception as e:
        click.echo(f"❌ Test failed: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def list_folders(ctx):
    """List all walkthrough folders and their VTT files."""
    config = ctx.obj['config']
    
    try:
        walkthroughs_path = Path(config.input_folder)
        
        if not walkthroughs_path.exists():
            click.echo(f"❌ Walkthroughs directory not found: {walkthroughs_path}", err=True)
            sys.exit(1)
        
        folders_with_vtt = []
        folders_without_vtt = []
        
        for item in walkthroughs_path.iterdir():
            if item.is_dir():
                vtt_files = list(item.glob("*.vtt"))
                summary_exists = (item / config.output_filename).exists()
                
                if vtt_files:
                    folders_with_vtt.append({
                        'name': item.name,
                        'vtt_file': vtt_files[0].name,
                        'summary_exists': summary_exists,
                        'multiple_vtt': len(vtt_files) > 1
                    })
                else:
                    folders_without_vtt.append(item.name)
        
        click.echo(f"📁 Walkthrough folders in {walkthroughs_path}:\\n")
        
        if folders_with_vtt:
            click.echo("✅ Folders with VTT files:")
            for folder in sorted(folders_with_vtt, key=lambda x: x['name']):
                status = "📝" if folder['summary_exists'] else "📄"
                warning = " ⚠️ (multiple VTT files)" if folder['multiple_vtt'] else ""
                click.echo(f"  {status} {folder['name']} - {folder['vtt_file']}{warning}")
        
        if folders_without_vtt:
            click.echo("\\n❌ Folders without VTT files:")
            for folder in sorted(folders_without_vtt):
                click.echo(f"  📁 {folder}")
        
        click.echo(f"\\n📊 Summary: {len(folders_with_vtt)} folders with VTT files, "
                  f"{len(folders_without_vtt)} without")
        
        summaries_exist = sum(1 for f in folders_with_vtt if f['summary_exists'])
        if summaries_exist > 0:
            click.echo(f"📝 {summaries_exist} folders already have summary files")
        
    except Exception as e:
        click.echo(f"❌ Error listing folders: {str(e)}", err=True)
        sys.exit(1)


def _display_text_results(results: dict):
    """Display processing results in a human-readable format."""
    click.echo("\\n" + "="*60)
    click.echo("🎯 PROCESSING RESULTS")
    click.echo("="*60)
    
    click.echo(f"📊 Total folders: {results['total_folders']}")
    click.echo(f"✅ Successfully processed: {results['processed']}")
    click.echo(f"⏭️  Skipped (already exist): {results['skipped']}")
    click.echo(f"❌ Errors: {results['errors']}")
    
    if results['results']:
        click.echo("\\n📋 Detailed Results:")
        
        for result in results['results']:
            status_icon = {
                'success': '✅',
                'skipped': '⏭️ ',
                'error': '❌'
            }.get(result['status'], '❓')
            
            click.echo(f"  {status_icon} {result['folder']}")
            
            if result['status'] == 'success' and 'processing_time' in result:
                click.echo(f"     ⏱️  {result['processing_time']['total_time']}s")
            elif result['status'] == 'error' and 'error' in result:
                click.echo(f"     💥 {result['error']}")


if __name__ == '__main__':
    cli()
