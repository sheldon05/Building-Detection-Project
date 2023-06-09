import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision.datasets import VOCDetection
from torchvision.transforms import transforms
from torch.utils.data import DataLoader
from pprint import pprint
import os
import time


"""Let the training begin!"""
checkpoint_folder = "/content/drive/MyDrive/model_checkpoint"
checkpoint_path = os.path.join(checkpoint_folder, "checkpoint.pt ")
best_model_path = os.path.join(checkpoint_folder, "best.pt ")


metric = MeanAveragePrecision()

def train(model, optimizer, train_loader, valid_loader, lr_scheduler):
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    model.to(device)
    num_epochs = 20
    start_epoch = 0
    best_mAP = -1

    if 'checkpoint.pt' in os.listdir(checkpoint_folder):
        print('..............Checkpoint Loaded................')
        checkpoint = torch.load(checkpoint_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        start_epoch = checkpoint['epoch'] + 1
        best_mAP = checkpoint['best_mAP']

    for epoch in range(start_epoch, num_epochs):
        running_loss = 0.0
        train_total_of_samples = 0

        print(f"........................Starting Epoch: {epoch}...........................")
        model.train()
        print('.............Training................')

        start_time = time.time()
        for batch_idx, (images, targets) in enumerate(train_loader):
            images = [image.to(device) for image in images]
            targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
            loss_dict = model(images, targets)
            losses = sum(loss for loss in loss_dict.values())
            running_loss += losses.item()
            train_total_of_samples += len(targets)
            writer.add_scalar('Training Loss', losses.item(), epoch * len(train_loader) + batch_idx)
            optimizer.zero_grad()
            losses.backward()
            optimizer.step()

            if batch_idx % 10 == 4:
              elapsed_time = time.time() - start_time
              avg_loss = running_loss / train_total_of_samples
              print(f'Batch[{batch_idx+1}/{len(train_loader)}], Avg. Loss: {avg_loss:.4f}, Time: {elapsed_time:.2f}s')

        lr_scheduler.step()

        print('...............Validation.................')
        model.eval()
        with torch.no_grad():
            all_predictions = []
            all_targets = []
            for batch_idx, (images, targets) in enumerate(valid_loader):
                images = [image.to(device) for image in images]
                targets = [{k: v.to(device) for k, v in t.items()} for t in targets]
                predict = model(images)
                for pred in predict:
                    all_predictions.append(pred)
                for targ in targets:
                    all_targets.append(targ)


            metric.update(all_predictions, all_targets)
            print('..............Mean Average Presition Metric...........')
            pprint(metric.compute())
            mAP = metric.compute()['map'].item()

            if mAP > best_mAP:
                best_mAP = mAP
                # Save the best model
                torch.save(model.state_dict(), best_model_path)


        # Save a checkpoint of the model and optimizer
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict(),
            'best_mAP': best_mAP
        }
        torch.save(checkpoint, checkpoint_path)
        print("..............Checkpoint Saved...............")
        # Print the loss and accuracy for the epoch
        print(f'Ending Epoch {epoch}/{num_epochs}, Epoch Loss: {running_loss/len(train_loader.dataset):.4f}, Epoch mAP: {mAP}')