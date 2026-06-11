import kagglehub

# Download latest version
path = kagglehub.dataset_download("osamahosamabdellatif/high-quality-invoice-images-for-ocr", output_dir="./data")

print("Path to dataset files:", path)