This folder contains the local deployment configuration for the demo services. It includes:
- `docker-compose.yml` - Docker Compose configuration for running the demo services locally
- `proxy.conf` - Nginx proxy configuration for routing between services
- `.env` - Environment variables for service paths

To run the services locally, navigate to the `local-deploy` folder and run:
```bash
docker-compose up
```