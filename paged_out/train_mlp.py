from tinygrad import Tensor, nn
import csv
import numpy as np

training_end_index = 1000
eval_items = 0
eval_items = 1000
epoch_num = 10000
lr = 0.001

with open("data/mnist_train.csv") as csvfile:
    reader = csv.reader(csvfile)
    x = []
    y = []
    for index, row in enumerate(reader):
        if index == 0:
            continue
        if index > training_end_index:
            break
        y.append(int(row[0]))
        x += [list(map(lambda x: float(x) / 255.0, row[1:]))]

x = Tensor(x, device="nv")
y = Tensor(y, device="nv")


def find_important_pixels(x: Tensor, top_k: int = 38):
    pixel_variance = x.var(axis=0)  # (784,)

    _, indices = pixel_variance.topk(top_k)
    return indices.numpy()


important_pixels = find_important_pixels(x)
print("Selected pixel indices:", important_pixels)
with open("data/important_pixels.csv", mode="w") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(important_pixels)
    for i in range(len(important_pixels)):
        writer.writerow([important_pixels[i]])


class MLP:
    def __init__(self, important_pixels):
        self.pixel_indices = important_pixels
        self.l1 = Tensor.kaiming_uniform(len(important_pixels), 10).to("nv")

    def __call__(self, x: Tensor):
        selected_pixels = x[
            :,
            self.pixel_indices
            if isinstance(self.pixel_indices, list)
            else self.pixel_indices.tolist(),
        ]
        return selected_pixels.dot(self.l1)


# verify if important_pixels are the same as precomputed ones (only for debugging/assert purposes, might remove later)
precomputed_important_pixels = [
    378,
    406,
    379,
    627,
    183,
    626,
    433,
    461,
    628,
    491,
    437,
    434,
    409,
    237,
    382,
    186,
    270,
    629,
    630,
    185,
    405,
    464,
    410,
    603,
    465,
    347,
    574,
    242,
    602,
    212,
    271,
    184,
    438,
    598,
    597,
    265,
    241,
    575,
]

same = True
for i, pixel in enumerate(important_pixels):
    if not same:
        break

    same = pixel == precomputed_important_pixels[i]

print(f"Important pixels{'' if same else " DON'T"} match the precomputed ones")

model = MLP(important_pixels)


optim = nn.optim.Adam([model.l1], lr=lr)


with Tensor.train():
    for i in range(epoch_num):
        optim.zero_grad()
        loss = model(x).sparse_categorical_crossentropy(y).backward()
        optim.step()
        print(i, loss.item())

print("Weights for first hidden neuron:", model.l1[:, 0].numpy())


state_dict = nn.state.get_state_dict(model)
l1 = np.frombuffer(state_dict.get("l1").data(), dtype=np.float32)
print("First few weights from l1:", l1[:10])

print(f"l1.size {l1.size}")

with open("data/model_weights.csv", mode="w") as csvfile:
    writer = csv.writer(csvfile)
    for i in range(l1.size):
        writer.writerow([l1[i]])

# run
total = 0
correct = 0
with open("data/mnist_train.csv") as csvfile:
    reader = csv.reader(csvfile)
    x = []
    y = []
    print("y_pred, y")
    for index, row in enumerate(reader):
        if index == 0 or index <= training_end_index:
            continue
        if index > training_end_index + eval_items:
            break

        x = Tensor([list(map(lambda x: float(x) / 255.0, row[1:]))], device="nv")
        y_pred = model(x)
        print(np.argmax(np.frombuffer(y_pred.data(), dtype=np.float32)), int(row[0]))
        total += 1
        if int(row[0]) == int(
            np.argmax(np.frombuffer(y_pred.data(), dtype=np.float32))
        ):
            correct += 1

print(f"Accuracy: {float(correct / total)} ({correct}/{total})")

# trained for ~5 minutes, validation accuracy 72%, not bad!
