from ultralytics import YOLO


def main():
    
    model = YOLO("brand.pt")

    model.train(
        
        data="brand_dataset",
        epochs=50,
        imgsz=224,
        batch=16,
        patience=15,
        lr0=0.003,
        
        freeze=5,
        device=0,
        project="runs/brand_finetune",
        name="station_makes",
    )


if __name__ == "__main__":
    main()
