import pathlib, sys, torch
pathlib.PosixPath = pathlib.PurePosixPath  # the checkpoint was saved on Linux; its hyperparameters hold Linux paths
ckpt = torch.load(sys.argv[1], map_location='cpu', weights_only=False)
torch.save({'state_dict': ckpt['state_dict']}, sys.argv[2])
print(len(ckpt['state_dict']), 'tensors; epoch', ckpt.get('epoch'), 'step', ckpt.get('global_step'))
