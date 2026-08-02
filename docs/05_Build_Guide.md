# Preferred Build Strategy

Do not continue hacking the prototype. Treat this repository as the source of truth.

1. Freeze the architecture and API contract
2. Build the backend against a mock provider
3. Build the frontend against the internal API
4. Integrate live aircraft data behind the provider abstraction
5. Enable appliance mode and the custom splash
6. Test touch, offline recovery and long-running operation
7. Create a reproducible release image
8. Produce gift-ready documentation

## Development run

```bash
./scripts/run-dev.sh
```

Open `http://localhost:8080`. The default mock provider needs no account, token or internet connection.

## Tests

```bash
PYTHONPATH=backend python3 -m unittest discover -s tests -v
```

