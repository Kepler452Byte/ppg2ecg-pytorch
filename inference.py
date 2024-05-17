from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import torch
from absl import app, flags

from modules.models import PPG2ECG


flags.DEFINE_string("weights", "logs/model/model_best.pth", "model weights for inferencing")
flags.DEFINE_string("input", "data/uqvitalsigns/uqvitalsignsdata-train/uq_vsd_case01_fulldata_02_08.npy", "input data (numpy array)")
FLAGS = flags.FLAGS


def main(argv):
    # prepare the parameters
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # prepare the model
    model = PPG2ECG(
        input_size=200,
        use_stn=True,
        use_attention=True).to(device)

    # load the model state
    model.load_state_dict(torch.load(Path(FLAGS.weights))["net"])
    model.eval()

    # prepare the inference data (PPG data)
    ppg = np.load(Path(FLAGS.input))
    print("Loaded PPG data from:", Path(FLAGS.input))
    print("PPG shape:", ppg.shape)
    ppg = ppg[0]
    # run through the data
    idx = 0
    step = 100
    ecg = []

    var = 1
    while var == 1:
        print(len(ppg))
        # out of range for ppg data
        if (idx + 200) > len(ppg):
            print("break")
            break
        # preprocess the single data to match the input size
        input_data = ppg[idx:idx + 200]

        # reshape the data to [1, 200]
        input_data = input_data.reshape((1, -1))

        # move ppg data to torch tensor and device
        input_data = torch.from_numpy(input_data).to(device).float()
        print(f"Input data at index {idx}: {input_data.shape}")

        # inference
        # in torch, you need (batch, data) for forward
        # so you should unsqueeze the input data by unsqueeze(0)
        # now the input size should be [1, 1, 200]
        with torch.no_grad():
            output_data = model(input_data.unsqueeze(0))
            print("torch")
            if "output" in output_data:
                output_tensor = output_data["output"].cpu()
                ecg.append(output_tensor[0, 0])  # [1, 1, 200] -> [200,]
                print(f"Appended ECG data of shape: {output_tensor[0, 0].shape}")
            else:
                print(f"No 'output' key in model output at index {idx}")

        idx += step

    if not ecg:
        raise ValueError("No ECG data was generated during inference. Please check the model and input data.")

    # model performs better in middle [50:150] for whole output [0:200]
    # also we drop first 50 and last 50 for ppg to align the ppg and ecg
    ecg = [e[50:150] for e in ecg]
    ppg = ppg[50:-50]

    # show the plot
    ecg = torch.cat(ecg)
    plt.plot(ppg, label="ppg")
    plt.plot(ecg, label="ecg")
    plt.legend()
    plt.show()


if __name__ == "__main__":
    app.run(main)
