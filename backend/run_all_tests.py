#!/usr/bin/env python3
"""
Run All Tests — Comprehensive Test Suite

Exécute tous les tests (représentatif + chatbot + E2E) et génère un rapport final.
"""

import subprocess
import sys
import json
import os
from pathlib import Path
from datetime import datetime


class TestRunner:
    """Coordonne l'exécution de tous les tests."""

    def __init__(self):
        self.results = []
        self.backend_dir = Path(__file__).parent
        self.reports_dir = self.backend_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)

    def run_command(self, cmd: list, description: str) -> bool:
        """Exécute une commande et retourne succès/échec."""
        print(f"\n{'='*70}")
        print(f"🚀 {description}")
        print(f"{'='*70}")
        print(f"Command: {' '.join(cmd)}")
        print()
        
        try:
            result = subprocess.run(cmd, cwd=self.backend_dir, timeout=300)
            success = result.returncode == 0
            
            if success:
                print(f"\n✅ {description} — PASSED")
            else:
                print(f"\n❌ {description} — FAILED (exit code: {result.returncode})")
            
            self.results.append({
                "test": description,
                "passed": success,
                "timestamp": datetime.now().isoformat()
            })
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"\n❌ {description} — TIMEOUT (>5min)")
            self.results.append({
                "test": description,
                "passed": False,
                "error": "Timeout",
                "timestamp": datetime.now().isoformat()
            })
            return False
        
        except Exception as e:
            print(f"\n❌ {description} — ERROR: {e}")
            self.results.append({
                "test": description,
                "passed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False

    def run_all_tests(self):
        """Exécute tous les tests."""
        print("\n" + "#"*70)
        print("# AI TALENT FINDER — COMPREHENSIVE TEST SUITE")
        print("#"*70)
        print(f"Backend directory: {self.backend_dir}")
        print(f"Reports directory: {self.reports_dir}")
        print(f"Start time: {datetime.now().isoformat()}")
        
        # Test 1: Representative Tests
        test1_passed = self.run_command(
            [sys.executable, "run_representative_tests.py"],
            "Test 1: Representative Tests (CV, Skills, Matching, Edge Cases)"
        )
        
        # Test 2: Chatbot Tests (optional, requires API key)
        if os.getenv("ANTHROPIC_API_KEY"):
            test2_passed = self.run_command(
                [sys.executable, "test_chatbot_recruiter_scenarios.py"],
                "Test 2: Chatbot Quality Tests"
            )
        else:
            print("\n⚠️  Test 2: Chatbot Quality Tests — SKIPPED (ANTHROPIC_API_KEY not set)")
            self.results.append({
                "test": "Test 2: Chatbot Quality Tests",
                "passed": None,
                "skipped": True,
                "reason": "ANTHROPIC_API_KEY not set",
                "timestamp": datetime.now().isoformat()
            })
            test2_passed = True
        
        # Test 3: E2E Tests (optional, requires frontend running)
        frontend_url = os.getenv("FRONTEND_URL")
        if frontend_url:
            test3_passed = self.run_command(
                [sys.executable, "test_e2e_recruiter_flow.py"],
                "Test 3: E2E Recruiter Flow Tests"
            )
        else:
            print("\n⚠️  Test 3: E2E Recruiter Flow Tests — SKIPPED (FRONTEND_URL not set)")
            self.results.append({
                "test": "Test 3: E2E Recruiter Flow Tests",
                "passed": None,
                "skipped": True,
                "reason": "FRONTEND_URL not set",
                "timestamp": datetime.now().isoformat()
            })
            test3_passed = True
        
        # Print overall summary
        self.print_summary()
        
        # Save comprehensive report
        self.save_report()
        
        # Return success if all required tests passed
        all_passed = all(r.get("passed", True) for r in self.results if not r.get("skipped"))
        return all_passed

    def print_summary(self):
        """Affiche un résumé des résultats."""
        print("\n" + "="*70)
        print("TEST EXECUTION SUMMARY")
        print("="*70)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r.get("passed", False))
        failed = sum(1 for r in self.results if r.get("passed", False) == False)
        skipped = sum(1 for r in self.results if r.get("skipped", False))
        
        print(f"\n📊 Results:")
        print(f"   ✅ Passed:  {passed}/{total}")
        print(f"   ❌ Failed:  {failed}/{total}")
        print(f"   ⏭️  Skipped: {skipped}/{total}")
        
        print(f"\n📋 Details:")
        for result in self.results:
            test_name = result.get("test", "unknown")
            if result.get("skipped"):
                reason = result.get("reason", "unknown")
                print(f"   ⏭️  {test_name}")
                print(f"      Reason: {reason}")
            elif result.get("passed"):
                print(f"   ✅ {test_name}")
            else:
                error = result.get("error", "unknown")
                print(f"   ❌ {test_name}")
                if error:
                    print(f"      Error: {error}")
        
        print()

    def save_report(self):
        """Sauvegarde un rapport JSON complet."""
        report_path = self.reports_dir / "test_suite_final_report.json"
        
        final_report = {
            "title": "AI Talent Finder — Comprehensive Test Suite",
            "execution_date": datetime.now().isoformat(),
            "backend_path": str(self.backend_dir),
            "backend_env": {
                "PYTHONPATH": os.getenv("PYTHONPATH", ""),
                "VIRTUAL_ENV": os.getenv("VIRTUAL_ENV", ""),
                "CONDA_DEFAULT_ENV": os.getenv("CONDA_DEFAULT_ENV", ""),
            },
            "test_results": self.results,
            "summary": {
                "total_tests": len(self.results),
                "passed": sum(1 for r in self.results if r.get("passed", False)),
                "failed": sum(1 for r in self.results if r.get("passed", False) == False),
                "skipped": sum(1 for r in self.results if r.get("skipped", False)),
            }
        }
        
        with open(report_path, "w") as f:
            json.dump(final_report, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_path}")
        
        # Also save to a txt version for readability
        txt_path = self.reports_dir / "test_suite_final_report.txt"
        with open(txt_path, "w") as f:
            f.write("="*70 + "\n")
            f.write("AI TALENT FINDER — COMPREHENSIVE TEST SUITE\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Execution Date: {datetime.now().isoformat()}\n")
            f.write(f"Backend Path: {self.backend_dir}\n\n")
            
            f.write("RESULTS\n")
            f.write("-"*70 + "\n")
            
            for result in self.results:
                test_name = result.get("test", "unknown")
                timestamp = result.get("timestamp", "")
                
                if result.get("skipped"):
                    reason = result.get("reason", "unknown")
                    f.write(f"⏭️  {test_name}\n")
                    f.write(f"   Status: SKIPPED\n")
                    f.write(f"   Reason: {reason}\n")
                elif result.get("passed"):
                    f.write(f"✅ {test_name}\n")
                    f.write(f"   Status: PASSED\n")
                else:
                    error = result.get("error", "unknown")
                    f.write(f"❌ {test_name}\n")
                    f.write(f"   Status: FAILED\n")
                    if error:
                        f.write(f"   Error: {error}\n")
                
                if timestamp:
                    f.write(f"   Timestamp: {timestamp}\n")
                f.write("\n")
            
            f.write("="*70 + "\n")
            f.write("SUMMARY\n")
            f.write("-"*70 + "\n")
            f.write(f"Total Tests: {len(self.results)}\n")
            f.write(f"Passed: {sum(1 for r in self.results if r.get('passed', False))}\n")
            f.write(f"Failed: {sum(1 for r in self.results if r.get('passed', False) == False)}\n")
            f.write(f"Skipped: {sum(1 for r in self.results if r.get('skipped', False))}\n")
        
        print(f"📄 Text report saved to: {txt_path}")


def main():
    """Main entry point."""
    print("""
    
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║           AI TALENT FINDER — COMPREHENSIVE TEST SUITE               ║
    ║                                                                      ║
    ║  Tests: Representative | Chatbot | E2E                              ║
    ║  Reports: JSON + Text + Per-test artifacts                          ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    print("CONFIGURATION")
    print("-"*70)
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Executable: {sys.executable}")
    
    api_key_set = bool(os.getenv("ANTHROPIC_API_KEY"))
    frontend_url = os.getenv("FRONTEND_URL")
    
    print(f"ANTHROPIC_API_KEY: {'✅ SET' if api_key_set else '❌ NOT SET'} (chatbot tests: {'enabled' if api_key_set else 'skipped'})")
    print(f"FRONTEND_URL: {'✅ SET' if frontend_url else '❌ NOT SET'} (E2E tests: {'enabled' if frontend_url else 'skipped'})")
    print()
    
    runner = TestRunner()
    success = runner.run_all_tests()
    
    print("\n" + "#"*70)
    if success:
        print("# ✅ ALL TESTS PASSED — SYSTEM READY FOR PRODUCTION")
    else:
        print("# ❌ SOME TESTS FAILED — SEE REPORTS FOR DETAILS")
    print("#"*70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
