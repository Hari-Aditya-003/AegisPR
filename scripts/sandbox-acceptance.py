"""Run real isolated fixture checks, without any model/provider requests.

Execute inside the backend container after deployment. Requires Docker socket
access already granted to that service. Creates and removes only its own
temporary fixture directories/images/containers.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from app.schemas.verification import GeneratedTest, RepositoryProfile
from app.services.sandbox import DockerSandbox


def check(language: str, root: Path) -> dict:
    if language == "python":
        profile = RepositoryProfile(languages=["Python"], test_framework="pytest",
                                    install_command="pip install -r requirements.txt", test_command="pytest -q")
        (root / "requirements.txt").write_text("pytest==9.1.1\n")
        (root / "test_existing.py").write_text("from coupon import coupon\ndef test_normal(): assert coupon(20,5)==15\n")
        generated = GeneratedTest(id="T1", hypothesis_id="H1", framework="pytest", file_path="test_generated.py",
                                  test_code="from coupon import coupon\ndef test_floor(): assert coupon(10,20)==0\n")
        source, good, bad = "coupon.py", "def coupon(t,d): return max(0,t-d)\n", "def coupon(t,d): return t-d\n"
    else:
        profile = RepositoryProfile(languages=["JavaScript"], test_framework="vitest",
                                    install_command="npm install --ignore-scripts", test_command="npm test -- --run",
                                    build_command="npm run build")
        (root / "package.json").write_text(json.dumps({"name": "aegispr-check", "private": True, "type": "module",
            "scripts": {"test": "vitest", "build": "node -e \"require('node:fs').mkdirSync('dist',{recursive:true})\""},
            "devDependencies": {"vitest": "5.0.3"}}))
        (root / "existing.test.js").write_text("import {test,expect} from 'vitest'; import {coupon} from './coupon.js'; test('normal',()=>expect(coupon(20,5)).toBe(15));\n")
        generated = GeneratedTest(id="T1", hypothesis_id="H1", framework="vitest", file_path="generated.test.js",
            test_code="import {test,expect} from 'vitest'; import {coupon} from './coupon.js'; test('floor',()=>expect(coupon(10,20)).toBe(0));\n")
        source, good, bad = "coupon.js", "export const coupon=(t,d)=>Math.max(0,t-d);\n", "export const coupon=(t,d)=>t-d;\n"
    sandbox = DockerSandbox(180, "1g", 1)
    results = {}
    for branch, contents in (("base", good), ("head", bad)):
        (root / source).write_text(contents)
        result = sandbox.execute(root, ("a" if branch == "base" else "b") * 40, branch, profile, generated)
        results[branch] = result.status.value
        if result.status.value not in {"PASSED", "FAILED"}:
            raise RuntimeError(
                f"{language} {branch}: {result.status.value}\n"
                f"stdout:\n{result.stdout[-4000:]}\nstderr:\n{result.stderr[-1500:]}"
            )
        (root / generated.file_path).unlink(missing_ok=True)
    (root / source).write_text(good)
    checks = sandbox.verify_repair(root, "b" * 40, profile, generated)
    results["manual_repair"] = {item.name: item.execution.status.value for item in checks}
    assert results["base"] == "PASSED" and results["head"] == "FAILED", results
    assert all(item.execution.status.value == "PASSED" for item in checks if item.command), results
    return results


if __name__ == "__main__":
    for language in ("python", "node"):
        with TemporaryDirectory(prefix="aegispr-acceptance-") as temporary:
            print(json.dumps({language: check(language, Path(temporary))}), flush=True)
