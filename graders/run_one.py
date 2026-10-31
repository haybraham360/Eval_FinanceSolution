"""Grades one solution file in this process. Always started by evalcore.grade_file in a
child process, so that a broken or hostile solution cannot touch the harness or its keys.

usage: python -I run_one.py <graders_dir> <task_id> <solution_path>
"""
import importlib
import importlib.util
import json
import resource
import socket
import sys


def main():
    graders_dir, task_id, solution_path = sys.argv[1:4]
    sys.path.insert(0, graders_dir)
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))
    resource.setrlimit(resource.RLIMIT_FSIZE, (10_000_000, 10_000_000))

    def no_network(*a, **k):
        raise PermissionError("network is disabled during grading")

    socket.socket = no_network
    socket.create_connection = no_network

    grader = importlib.import_module(task_id)
    if getattr(grader, "KIND", "python") == "json":
        with open(solution_path) as f:
            target = f.read()
    else:
        spec = importlib.util.spec_from_file_location("solution", solution_path)
        target = importlib.util.module_from_spec(spec)
        sys.modules["solution"] = target
        try:
            spec.loader.exec_module(target)
        except BaseException as exc:
            print(json.dumps({"load_error": f"{type(exc).__name__}: {exc}"[:800]}))
            return
    print("\n@@RESULT@@" + json.dumps({"checks": grader.CHECKS.run(target)}))


main()
