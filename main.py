"""Training script."""

# Imports.
import os
from os.path import join, isfile
import argparse
import random
from random import shuffle
import pickle

import tensorflow as tf
from tensorflow.contrib.eager.python import tfe

from model import SiameseStereoMatching
from dataset import Dataset

# Enable eager execution.
tf.enable_eager_execution()


# Parse args.
parser = argparse.ArgumentParser(
    description='Re-implementation of Efficient Deep Learning for Stereo Matching')
parser.add_argument('--resume', '-r', default=False, help='resume from checkpoint')
parser.add_argument('--exp-name', default='debug', type=str,
                    help='name of experiment')
parser.add_argument('--log-level', default='INFO', choices = ['DEBUG', 'INFO'],
                    help='log-level to use')
parser.add_argument('--batch-size', default=128, help='batch-size to use')
parser.add_argument('--dataset', default='kitti_2015', choices=['kitti_2012',
                                                                'kitti_2015'],
                    help='dataset')
parser.add_argument('--seed', default=3, help='random seed')
parser.add_argument('--patch-size', default=37, help='patch size from left image')
parser.add_argument('--disparity-range', default=201, help='disparity range')
parser.add_argument('--learning-rate', default=0.01, help='initial learning rate')
parser.add_argument('--find-patch-locations', default=False,
                    help='find and store patch locations')
parser.add_argument('--num_iterations', default=40000,
                    help='number of training iterations')

settings = parser.parse_args()


# Settings, hyper-parameters.
setattr(settings, 'phase', 'training')
setattr(settings, 'data_path', join('data', settings.dataset, settings.phase))
setattr(settings, 'out_cache_path', join('cache', settings.dataset,
                                         settings.phase))
setattr(settings, 'img_height', 370)
setattr(settings, 'img_width', 1224)
setattr(settings, 'half_patch_size', (settings.patch_size // 2))
setattr(settings, 'half_range', settings.disparity_range // 2)
setattr(settings, 'num_train', 160)

if settings.dataset == 'kitti_2012':
    setattr(settings, 'left_img_folder', 'image_0')
    setattr(settings, 'right_img_folder', 'image_1')
    setattr(settings, 'disparity_folder', 'disp_noc')
    setattr(settings, 'num_val', 34)
elif settings.dataset == 'kitti_2015':
    setattr(settings, 'left_img_folder', 'image_2')
    setattr(settings, 'right_img_folder', 'image_3')
    setattr(settings, 'disparity_folder', 'disp_noc_1')
    setattr(settings, 'num_val', 40)


# Set random seed, so train/val split remains same.
random.seed(settings.seed)


# Patch locations.
patch_locations_path = join(settings.out_cache_path, 'patch_locations.pkl')
if settings.find_patch_locations or not isfile(patch_locations_path):
    find_and_store_patch_locations()
with open(patch_locations_path, 'rb') as handle:
    patch_locations = pickle.load(handle)


# Model.
device = '/cpu:0' if tfe.num_gpus() == 0 else '/gpu:0'
with tf.device(device):
    model = SiameseStereoMatching(1, device)


# Optimizer
optimizer = tf.train.AdagradOptimizer(learning_rate=settings.learning_rate)


# Dataset iterators.
training_dataset = Dataset(settings, patch_locations, phase='train')
validation_dataset = Dataset(settings, patch_locations, phase='val')


model.fit(training_dataset, validation_dataset, optimizer,
          settings.num_iterations)