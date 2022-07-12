import cv2
import torch
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2

model_path = 'model/cats.pt'
classes = {0: 'Other', 1: 'Cat'}

transform = A.Compose(
    [
        A.Resize(224, 224, interpolation=cv2.INTER_AREA),
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2(),
    ]
)

model = torch.load(model_path, map_location=torch.device('cpu'))


def preprocessing(image):
    raw_image = image
    if type(raw_image) == bytes:
        raw_image = cv2.imdecode(np.frombuffer(raw_image, np.uint8), -1)
    image = cv2.cvtColor(raw_image, cv2.COLOR_BGR2RGB)
    if transform is not None:
        image = transform(image=image)["image"]
    image = image.view(1, 3, 224, 224).to('cpu').detach()
    return image


def img_predict(img_path):
    img = cv2.imread(img_path)
    model.eval()
    with torch.no_grad():
        output = model(preprocessing(img))
        prob = float(torch.sigmoid(output)[:, 0].cpu().numpy())
        pred_classes = int((torch.sigmoid(output) >= 0.5)[:, 0].cpu().numpy())
    return prob, classes[pred_classes]


assert img_predict('model/test_image.jpg')[1] == 'Cat', 'Model error!'
