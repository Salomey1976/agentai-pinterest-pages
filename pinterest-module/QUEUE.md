# Google Drive queue

The local queue root is `G:\Мой диск\Pinterest`.

- `Изображения`: source JPEG or PNG files;
- `Очередь`: one JSON job per pending Pin;
- `Опубликовано`: jobs, images, and API receipts after a successful real publication;
- `Ошибки`: a job moved here only when a real publication attempt failed.

## Create a job

1. Copy an image, for example `example.jpg`, into `G:\Мой диск\Pinterest\Изображения`.
2. Copy `queue.job.example.json` to `G:\Мой диск\Pinterest\Очередь\example.json`.
3. Edit the copy. The `image` value must exactly match the file name in `Изображения`.
4. Set `board_id` to the desired Pinterest board. The current known AI board is `618682136250788239`.

## Validate without publishing

```powershell
python queue_processor.py --job example.json
```

This validates the image and prints a payload. It does not create a Pin or move any file.

## Publish one reviewed job

```powershell
python queue_processor.py --job example.json --publish
```

This is the only command that creates a Pin. On success it moves the job and image to `Опубликовано` and saves the Pinterest result JSON there.

## Process all queued jobs

```powershell
python queue_processor.py
# after review and explicit approval:
python queue_processor.py --publish
```

The processor encodes local JPEG and PNG images for Pinterest using `image_base64`; no external image host is needed.
