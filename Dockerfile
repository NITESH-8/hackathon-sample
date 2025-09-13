Backend: added pytest and pytest-cov to requirements.txt
Run: pytest -q or pytest --cov=.
Frontend: added testing libs to package.json devDependencies
Run: npm test -- --watchAll=false
Docs: README.md now points to tests/README.md
Note:
Some tests use live endpoints or the Flask test client. For the integration/perf tests, ensure the app is running at http://localhost:5000.
