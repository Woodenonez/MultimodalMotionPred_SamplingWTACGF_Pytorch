import os
import glob

import numpy as np
import pandas as pd

import torch
from torch.utils.data import Dataset, DataLoader, random_split

from skimage import io, transform


class DataHandler():
    def __init__(self, dataset, batch_size=64, shuffle=True, validation_prop=0.2, validation_cache=64):
        self.__val_p = validation_prop
        self.dataset = dataset
        if 0<validation_prop<1:
            self.split_dataset()
        else:
            self.dataset_train = self.dataset
            self.dataset_val = []
            self.dl_val = []

        self.dl = DataLoader(self.dataset_train, batch_size, shuffle) # create the dataloader from the dataset
        self.__iter = iter(self.dl)

        if self.dataset_val:
            self.dl_val = DataLoader(self.dataset_val, batch_size=validation_cache, shuffle=shuffle)
            self.__iter_val = iter(self.dl_val)

    def split_dataset(self):
        ntraining = int(self.return_length_ds(whole_dataset=True) * (1-self.__val_p))
        nval = self.return_length_ds(whole_dataset=True) - ntraining
        self.dataset_train, self.dataset_val = random_split(self.dataset, [ntraining, nval])

    def return_batch(self):
        try:
            sample_batch = next(self.__iter)
        except StopIteration:
            self.reset_iter()
            sample_batch = next(self.__iter)
        return sample_batch['image'], sample_batch['label']

    def return_val(self):
        try:
            sample_batch = next(self.__iter_val)
        except StopIteration:
            self.__iter_val = iter(self.dl_val)
            sample_batch = next(self.__iter_val)
        image, label = sample_batch['image'], sample_batch['label']
        if len(image.shape)==3:
            image = image.unsqueeze(0)
            label = label.unsqueeze(0)
        return image, label

    def reset_iter(self):
        self.__iter = iter(self.dl)

    def return_length_ds(self, whole_dataset=False):
        if whole_dataset:
            return len(self.dataset)
        else:
            return len(self.dataset_train), len(self.dataset_val)

    def return_length_dl(self):
        return len(self.dl) # the number of batches, only for training dataset


class ImageStackDataset(Dataset):
    def __init__(self, csv_path, root_dir, channel_per_image, transform=None, T_channel=False):
        '''
        Args:
            csv_path: Path to the CSV file with dataset info.
            root_dir: Directory with all image folders.
                      root_dir - obj_folder - obj & env
        '''
        super().__init__()
        self.info_frame = pd.read_csv(csv_path)
        self.root_dir = root_dir
        self.tr = transform
        self.with_T = T_channel
        self.cpi = channel_per_image

        self.nc = len(list(self.info_frame))-4 # number of image channels in total
        self.img_shape = self.check_img_shape()

    def __len__(self):
        return len(self.info_frame)

    def __getitem__(self,idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        input_img = np.empty(shape=[self.img_shape[0],self.img_shape[1],0])
        info = self.info_frame.iloc[idx]
        self.T = info['T']
        index = info['index']
        traj = []
        for i in range(self.nc):
            img_name = info['f{}'.format(i)]
            obj_id = img_name.split('_')[0]

            if self.cpi == 1:
                img_path = os.path.join(self.root_dir, obj_id, img_name)
                this_x = float(img_name[:-4].split('_')[2])
                this_y = float(img_name[:-4].split('_')[3])
                traj.append([this_x,this_y])
            elif self.cpi == 2:
                if len(img_name.split('_'))==5:
                    img_path = os.path.join(self.root_dir, obj_id, 'obj', img_name)
                    time_step = int(img_name[:-4].split('_')[1])
                    this_x = float(img_name[:-4].split('_')[2])
                    this_y = float(img_name[:-4].split('_')[3])
                    traj.append([this_x,this_y])
                else:
                    img_path = os.path.join(self.root_dir, obj_id, 'env', img_name)

            image = self.togray(io.imread(img_path))
            input_img = np.concatenate((input_img, image[:,:,np.newaxis]), axis=2)

        if self.with_T:
            T_channel = np.ones(shape=[self.img_shape[0],self.img_shape[1],1])*self.T # T_channel
            input_img = np.concatenate((input_img, T_channel), axis=2)                # T_channel

        label = {'x':info['x'], 'y':info['y']}
        sample = {'image':input_img, 'label':label}

        if self.tr:
            sample = self.tr(sample)

        sample['index'] = index
        sample['traj'] = traj
        sample['time'] = time_step

        return sample

    def togray(self, image):
        if (len(image.shape)==2):
            return image
        elif (len(image.shape)==3) and (image.shape[2]==1):
            return image[:,:,0]
        else:
            image = image[:,:,:3] # ignore alpha
            img = image[:,:,0]/3 + image[:,:,1]/3 + image[:,:,2]/3
            return img

    def check_img_shape(self):
        info = self.info_frame.iloc[0]
        img_name = info['f0']
        obj_id = img_name.split('_')[0]

        if self.cpi == 1:
            img_path = os.path.join(self.root_dir, obj_id, img_name)
        elif self.cpi == 2:
            img_path = os.path.join(self.root_dir, obj_id, 'obj', img_name)

        image = self.togray(io.imread(img_path))
        return image.shape

class ImageStackDatasetSDD(Dataset):
    def __init__(self, csv_path, root_dir, ext='.jpg', transform=None, T_channel=False):
        '''
        Args:
            csv_path: Path to the CSV file with dataset info.
            root_dir: Directory with all image folders.
                      root_dir - video_folder - imgs
        '''
        super().__init__()
        self.info_frame = pd.read_csv(csv_path)
        self.root_dir = root_dir
        self.tr = transform
        self.with_T = T_channel
        self.ext = ext

        self.nc = len(list(self.info_frame))-5 # number of image channels in half
        self.img_shape = self.check_img_shape()

        # print(self.img_shape)

    def __len__(self):
        return len(self.info_frame)

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()

        input_img = np.empty(shape=[self.img_shape[0],self.img_shape[1],0])
        info = self.info_frame.iloc[idx]
        T = info['T']
        index = info['index']
        traj = []
        for i in range(self.nc):
            img_name = info[f't{i}'].split('_')[0] + self.ext
            video_idx = info['index']

            img_path = os.path.join(self.root_dir, video_idx, img_name)

            csv_name = glob.glob(os.path.join(self.root_dir, video_idx, '*.csv'))
            original_scale = os.path.basename(csv_name[0]).split('.')[0]
            original_scale = (int(original_scale.split('_')[0]), int(original_scale.split('_')[1])) # HxW

            time_step = int(info[f't{i}'].split('_')[0])
            this_x = float(info[f't{i}'].split('_')[1])
            this_y = float(info[f't{i}'].split('_')[2])
            traj.append([this_x,this_y])

            image = self.togray(io.imread(img_path))
            input_img = np.concatenate((input_img, image[:,:,np.newaxis]), axis=2)

            white_canvas = np.zeros_like(image)
            obj_coords = self.rescale_label((this_x, this_y), original_scale)
            obj_map = self.np_gaudist_map(obj_coords, white_canvas, sigmas=[20,20])
            input_img = np.concatenate((input_img, obj_map[:,:,np.newaxis]), axis=2)

        if self.with_T:
            T_channel = np.ones(shape=[self.img_shape[0],self.img_shape[1],1])*T # T_channel
            input_img = np.concatenate((input_img, T_channel), axis=2)           # T_channel

        label = {'x':info['x'], 'y':info['y']}
        sample = {'image':input_img, 'label':label}

        if self.tr:
            sample = self.tr(sample)

        sample['index'] = index
        sample['traj'] = traj
        sample['time'] = time_step

        return sample

    @staticmethod
    def np_gaudist_map(centre, base_matrix, sigmas=[100,100], rho=0, flip=False):
        # Create a distance map given the centre and map size
        # The distance is defined by the Gaussian distribution
        # The map is normalized
        sigma_x, sigma_y = sigmas[0], sigmas[1]
        x = np.arange(0, base_matrix.shape[1])
        y = np.arange(0, base_matrix.shape[0])
        x, y = np.meshgrid(x, y)
        in_exp = -1/(2*(1-rho**2)) * ((x-centre[0])**2/(sigma_x**2) 
                                    + (y-centre[1])**2/(sigma_y**2) 
                                    - 2*rho*(x-centre[0])/(sigma_x)*(y-centre[1])/(sigma_y))
        z = 1/(2*np.pi*sigma_x*sigma_y*np.sqrt(1-rho**2)) * np.exp(in_exp)
        if flip:
            return 1 - z/z.max()
        else:
            return z/z.max()

    def rescale_label(self, label, original_scale): # x,y & HxW
        current_scale = self.check_img_shape()
        rescale = (current_scale[0]/original_scale[0] , current_scale[1]/original_scale[1])
        return (label[0]*rescale[1], label[1]*rescale[0])

    def togray(self, image):
        if (len(image.shape)==2):
            return image
        elif (len(image.shape)==3) and (image.shape[2]==1):
            return image[:,:,0]
        else:
            image = image[:,:,:3] # ignore alpha
            img = image[:,:,0]/3 + image[:,:,1]/3 + image[:,:,2]/3
            return img

    def check_img_shape(self):
        info = self.info_frame.iloc[0]
        img_name = info['t0'].split('_')[0] + self.ext
        video_folder = info['index']
        img_path = os.path.join(self.root_dir, video_folder, img_name)
        image = self.togray(io.imread(img_path))
        return image.shape


class Rescale(object):
    def __init__(self, output_size, tolabel=False):
        super().__init__()
        assert isinstance(output_size, tuple)
        self.output_size = output_size
        self.tolabel = tolabel

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        h, w = image.shape[:2]
        h_new, w_new = self.output_size

        img = transform.resize(image, (h_new,w_new))
        if self.tolabel:
            label['x'], label['y'] = label['x']*w_new/w, label['y']*h_new/h
        return {'image':img, 'label':label}

class ToGray(object):
    # For RGB the weight could be (0.299R, 0.587G, 0.114B)
    def __init__(self, weight=None):
        super().__init__()
        if weight is not None:
            assert (len(weight)==3)
            w1 = round(weight[0]/sum(weight),3)
            w2 = round(weight[1]/sum(weight),3)
            w3 = 1 - w1 - w2
            self.weight = (w1, w2, w3)
        else:
            self.weight = None

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        if (len(image.shape)==2) or (image.shape[2] == 1):
            return sample
        else:
            image = image[:,:,:3] # ignore alpha
            if self.weight is not None:
                img = self.weight[0]*image[:,:,0] + self.weight[1]*image[:,:,1] + self.weight[2]*image[:,:,2]
            else:
                img = image[:,:,0]/3 + image[:,:,1]/3 + image[:,:,2]/3
        return {'image':img[:,np.newaxis], 'label':label}

class DelAlpha(object):
    # From RGBA to RGB
    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        if (len(image.shape)==2) or (image.shape[2] == 1):
            return sample
        else:
            return {'image':image[:,:,:3], 'label':label}

class ToTensor(object):
    """Convert ndarrays in sample to Tensors."""

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        label = np.array([label['x'],label['y']])
        # swap color axis, numpy: H x W x C -> torch: C X H X W
        image = image.transpose((2, 0, 1))
        return {'image': torch.from_numpy(image),
                'label': torch.from_numpy(label)}

class MaxNormalize(object):
    def __init__(self, max_pixel=255, max_label=10):
        super().__init__()
        self.mp = max_pixel
        self.ml = max_label

    def __call__(self, sample):
        image, label = sample['image'], sample['label']
        if not isinstance(self.mp, (tuple,list)):
            self.mp = [self.mp]*image.shape[2]
        for i in range(image.shape[2]):
            image[:,:,:i] = image[:,:,:i]/self.mp[i]
        if self.ml is not None:
            if self.ml is tuple:
                label['x'], label['y'] = label['x']/self.ml[0], label['y']/self.ml[1]
            else:
                label['x'], label['y'] = label['x']/self.ml, label['y']/self.ml
        return {'image':image, 'label':label}

