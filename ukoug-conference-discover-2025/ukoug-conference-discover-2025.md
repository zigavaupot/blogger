![Just Streams AI Data Plaform](https://zigavaupot.github.io/blogger/ukoug-conference-discover-2025/images/just-streams-ai-data-plaform.png.png)

This year, I had the pleasure of joining the UKOUG Discover 2025 conference — a fantastic gathering of Oracle professionals, engineers, and data enthusiasts. Even more exciting, I had the opportunity to co-present with my colleague Sandi Holub, delivering (probably) one of the most hands-on sessions of the event.

Our session, titled **Just Streams: Real-Time Data Pipelines in OCI (with a Live Demo Twist)**, focused on exactly that: no slides, no theoretical diagrams — just real data in motion.

### A Session Built on Real-Time Everything

We set out to show what can be achieved when you combine streaming data, cloud-native services, and a bit of creativity. The entire session was structured around real, public data from Transport for London (TfL), and two live demonstrations:

1. Real-Time Bus Tracking and Arrival Analysis

We ingested live bus arrival data into OCI **Streaming**, processed it with OCI **Data Flow** (Apache Spark), and pushed curated results into **Oracle Analytics Cloud**.
The outcome: analysts could run SQL-based queries and visualize insights within seconds of the events occurring on the streets of London.

2. Real-Time Bus Movement Visualization

The second demo focused on GPS telemetry from TfL buses. Using **GoldenGate Stream Analytics**, we enriched streaming location data with route context and displayed it on a real-time dashboard — every location update brought the visualization to life.

While our examples came from public transport, the same architecture applies to real-world industry use cases — from manufacturing plants and steel mills to logistics, IoT networks, and sensor-heavy operations. We had even prepared a small ML/AI “cookie” which we didn't show at the end: showing how anomaly detection or predictive insights can be layered on top of streaming pipelines.

### A Last-Minute Twist: Rebuilding Everything on Oracle’s AI Data Platform

One month before **Discover 2025**, during **AI World** in **Las Vegas**, Oracle announced the **Oracle AI Data Platform (AIDP)** — a unified, AI-native architecture designed to bring together streaming, data engineering, machine learning, and analytics into a single, coherent ecosystem.

Sandi and I looked at each other (actually it was discussion over Teams) and said: **We’re doing this on AIDP.**

And so, at the very last minute, **we rebuilt the entire set of demos** on top of Oracle’s brand-new platform.

### The result?

**A fully working real-time streaming demo running natively on AIDP — feeding directly into Oracle Analytics for live reporting.**

By the time we arrived at UKOUG, our pipelines weren’t just running; they were performing better, cleaner, and more efficiently thanks to AIDP’s integrated architecture.

### A Few Words on the Oracle AI Data Platform (AIDP)

AIDP represents a major shift in how data and AI workloads are built on Oracle Cloud.
It brings together:
- High-throughput streaming and ingestion
- Unified lakehouse storage
- Distributed compute for Spark, Python, and AI workloads
- Built-in vector search and model serving
- Seamless integration with Oracle Analytics, GoldenGate Stream Analytics and the broader OCI ecosystem

For teams building real-time, AI-enabled data pipelines, AIDP eliminates fragmentation. Everything — from ingestion to enrichment to machine learning to analytics — connects through a single, AI-native fabric.

Our experience at UKOUG showed just how powerful that can be.

### A Conference to Remember

Presenting at UKOUG Discover 2025 was a fantastic experience, and doing it alongside Sandi made it even better. The energy in the room, the number of questions, and the excitement around real-time architectures and the new AI Data Platform were truly motivating.

With Oracle doubling down on AI-native data architectures, I’m confident this is just the beginning.
And we’re already preparing the next demo.

Download slides [here](https://zigavaupot.github.io/blogger/ukoug-conference-discover-2025/files/just-streams-and-ai-data-platform.pdf). 