#!/usr/bin/env python3
"""
Test Runner for VTT Summarizer

This script provides a convenient way to run different types of tests:
- E2E tests (end-to-end integration tests)
- Unit tests (individual component tests)
- All tests
"""

import sys
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("The 'yaml' module is not installed. Please install it using 'pip install pyyaml'.")
    sys.exit(1)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def run_e2e_tests():
    """Run end-to-end tests."""
    print("🚀 Running E2E Tests...")
    try:
        from tests.test_e2e import run_e2e_tests
        return run_e2e_tests()
    except ImportError as e:
        print(f"❌ Could not import E2E tests: {e}")
        return False


def run_unit_tests():
    """Run unit tests (placeholder for future unit tests)."""
    print("🧪 Running Unit Tests...")
    print("ℹ️  Unit tests not implemented yet. Run E2E tests for comprehensive testing.")
    return True


def run_all_tests():
    """Run all available tests."""
    print("🎯 Running All Tests...")
    
    e2e_success = run_e2e_tests()
    unit_success = run_unit_tests()
    
    success = e2e_success and unit_success
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    
    return success


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test Runner for VTT Summarizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_tests.py              # Run all tests
  python3 run_tests.py --e2e        # Run only E2E tests
  python3 run_tests.py --unit       # Run only unit tests
  python3 run_tests.py --help       # Show this help message
        """
    )
    
    parser.add_argument(
        '--e2e',
        action='store_true',
        help='Run end-to-end (E2E) tests only'
    )
    
    parser.add_argument(
        '--unit',
        action='store_true',
        help='Run unit tests only'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    # Determine which tests to run
    if args.e2e:
        success = run_e2e_tests()
    elif args.unit:
        success = run_unit_tests()
    else:
        success = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
