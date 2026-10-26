# Infrastructure validation

From repository root:

```sh
python -m pip install pyyaml
python Infrastructure/scripts/validate-catalog.py
```

This checks catalog shape and referenced paths only. It does not validate live DNS, service discovery, authorization or production readiness.
