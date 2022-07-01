Image Hosting App
-----------------

This app lets user upload images and retrieve them over REST APIs.

Users can
- Upload images in `png` or `jpg` format via HTTP request.
- List their uploaded images.
- Fetch image links as per their subscription plan.

Admin can
- Create users. And manage subscription.
- Create arbitrary account tiers.

APIs
-------
1. Ping Service
```bash
curl -X GET http://127.0.0.1:8080/api/ping
```
2. Upload Images
```bash
curl -L -X POST -S -u "username:password" \
     -F image_desc="some random image" \
     -F image_path='@"/path/to/image/someImage.png"' \
     -F image_uri_expiry_sec=400 \
     http://127.0.0.1:8080/api/image/
```
```
image_uri_expiry_sec: optional, int (300 - 30000 sec)'
```
3. List Images
```bash
curl -L -X GET -S -u "username:password" \
      http://127.0.0.1:8080/api/image/
```
4. Download Original Images
```bash
curl -X GET -u "username:password" \
     --remote-name --remote-header-name \
     http://localhost:8080/api/image/<image-uuid>/
```
5. Download Image Thumbnails
```bash
curl -L -X GET -u "username:password" \
     --remote-name --remote-header-name \
     http://localhost:8080/api/image/<image-uuid>/size/<thumbnail-size>/
```
6. Download Image with Temp URL
```bash
curl -L -X GET -u "username:password" \
     --remote-name --remote-header-name \
     http://localhost:8080/api/image/<image-temp-id>/
```

Develop
-------
See `Makefile` for quick commands.

- Install [docker-compose](https://docs.docker.com/compose) 

- This will clone the repo and start ImageHostingApp
  ```shell
  $ git clone https://github.com/virtualinit/imghostapp
  $ cd imghostapp/docker-compose
  $ sudo docker-compose up
  ```

- Application should be accessible at `localhost:8080`.
- Default login is `imghostapp`|`password`

Superuser can be created using `./manage.py createuser` command.
