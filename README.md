# 🧠 Oriel

**Semantic search, built for AI**

Oriel is a semantic search engine designed to help AI applications find meaning, not just keywords. Built in Rust for speed and reliability, it turns embeddings from your favorite neural network or encoder into a fast, filterable, production-ready search layer.

---

## ✨ Features

- **Semantic Vector Search** — find results by meaning using dense vector embeddings, not exact keyword matches
- **Payload Filtering** — attach structured metadata to your vectors and filter results with rich conditions
- **Fast & Reliable** — written in Rust for high performance, low latency, and safety even under heavy load
- **Simple API** — a clean interface for storing, searching, and managing your data
- **Docker-Ready** — ship and run Oriel anywhere with the included Dockerfile

## 🚀 Getting Started

### Run with Docker

```bash
docker build -t oriel .
docker run -p 6333:6333 oriel
```

### Build from Source

Oriel is written in Rust — you'll need the Rust toolchain installed.

```bash
git clone https://github.com/ATLURI0001/Oriel.git
cd Oriel
cargo build --release
cargo run --release
```

## 📦 Project Structure

```
├── .config/       # Project configuration
├── config/        # Runtime configuration files
├── docs/          # Documentation
├── lib/           # Core library code
├── openapi/       # OpenAPI / API specification
├── src/           # Main application source
├── tests/         # Test suite
├── tools/         # Developer tooling and scripts
├── Cargo.toml     # Rust package manifest
└── Dockerfile     # Container build definition
```

## 🛠️ Usage

Once running, connect to Oriel using its API to store vectors with an optional payload, then query by similarity:

```python
# Example — adjust to Oriel's actual client/API
from oriel_client import OrielClient

client = OrielClient(url="http://localhost:6333")

client.upsert(
    collection="my_data",
    points=[{"id": 1, "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"category": "example"}}]
)

results = client.search(collection="my_data", query_vector=[0.1, 0.2, 0.3, 0.4], limit=5)
```

> Update this section with Oriel's actual client library and endpoint details once finalized.

## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss significant changes before submitting a pull request.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch and open a PR

## 📄 License

This project is licensed under the terms of the license included in the [LICENSE](LICENSE) file.

## 📬 Contact

Have questions or suggestions? Open an issue on this repository.
