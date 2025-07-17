# TW3_backend

## Getting Started

This is the backend for TW3 Case study

### Docker Usage

1. Build the Docker image (from the project root):
   ```bash
   docker build -t tw3-back .
   ```
2. Run the Docker container:
   ```bash
   docker run -p 270:270 tw3-back
   ```

The app will be available at [http://localhost:270](http://localhost:270)


### Not yet implemented

To pull the image from github image registry just run
   ```bash
   docker pull ghcr.io/jclmantilla/tw3-back:latest
   ```