# -*- coding: utf-8 -*-
"""80-20 Split-EEGNET_Example.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1yhPZrxAXupwhsiaFkDTCvHndkpJC1K1K

TO Do List
As on 18th January 2022
- Output the difference in subject distributions using all the methods that were thought of
As on 19th January 2022
- Explore new ways to represent the difference in distributions of subject data and try training the subject data in reverse order and verify with the assumption that it's getting complex towards the end
As on 20th January 2022
- Present to Sir how the idea of 80-20 split didn't actually work with the confusion matrices accuracy graphs and across methods accuracy comparisions, and subject data distribution differences and how altering the frames count and its impact on the train and test accuracies

"
"""


#from google.colab import drive
#drive._mount('/content/drive')

#!wget https://raw.githubusercontent.com/vlawhern/arl-eegmodels/master/EEGModels.py

#!wget https://raw.githubusercontent.com/vlawhern/arl-eegmodels/master/EEGModels.py
from EEGModels import EEGNet, ShallowConvNet, DeepConvNet
#!pip install pyriemann
#!pip install mne

from EEGModels import EEGNet, ShallowConvNet, DeepConvNet

#!pip install pyriemann
#!pip install mne

from tensorflow.keras import utils as np_utils
from tensorflow.keras.callbacks import ModelCheckpoint
from tensorflow.keras import backend as K
from tensorflow.keras.optimizers import Adam
import csv
import pandas as pd
import numpy as np
from scipy.io import loadmat
import h5py 

# PyRiemann imports
from pyriemann.estimation import XdawnCovariances
from pyriemann.tangentspace import TangentSpace
from pyriemann.utils.viz import plot_confusion_matrix
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

import numpy as np

# mne imports
import mne
from mne import io
from mne.datasets import sample

from sklearn.metrics import precision_recall_fscore_support
from matplotlib import pyplot as plt
from collections import Counter

def get_subject_data(subject_numbers=[4], mod=False, print_info=True, norm=False, scale=True):
  #class 0 for ani and class 1 for ina
  global chans, samples, kernels

  for i, sn in enumerate(subject_numbers) :

    
    F1 = h5py.File(f"/content/drive/MyDrive/RA_handover/Subjects/{sn}/x.mat") #ani_clear x
    F2 = h5py.File(f"/content/drive/MyDrive/RA_handover/Subjects/{sn}/z.mat") #ina_clear z
    F3 = h5py.File(f"/content/drive/MyDrive/RA_handover/Subjects/{sn}/y.mat") #ani_blur  y
    F4 = h5py.File(f"/content/drive/MyDrive/RA_handover/Subjects/{sn}/p.mat") #ina_blur  p

    x, z, y, p = F1['x'][()], F2['z'][()], F3['y'][()], F4['p'][()]
    

    
    xnew, znew, ynew, pnew = np.moveaxis(x, [1, 2, 0], [0, 1, 2]), np.moveaxis(z, [1, 2, 0], [0, 1, 2]), np.moveaxis(y, [1, 2, 0], [0, 1, 2]), np.moveaxis(p, [1, 2, 0], [0, 1, 2])
   
    
    X_train_t = np.concatenate((xnew, znew), axis=0) #contains clear images of ani and ina
    X_test_t =  np.concatenate((ynew, pnew), axis=0) #contains blur  images of ani and ina

    ani_id = 0
    ina_id = 1

    Y_train_t=np.concatenate((np.full(xnew.shape[0],ani_id), np.full(znew.shape[0],ina_id)),axis=0) #labeling classes with 0 and 1 accordingly
    Y_test_t=np.concatenate((np.full(ynew.shape[0],ani_id), np.full(pnew.shape[0],ina_id)),axis=0) #labeling classes with 0 and 1 accordingly

    Y_train_t=np_utils.to_categorical(Y_train_t)
    Y_test_t=np_utils.to_categorical(Y_test_t)

    
    chans, samples, kernels = 50, 141, 1 


    X_train_t      = X_train_t.reshape(X_train_t.shape[0], chans, samples, kernels)
    X_test_t       = X_test_t.reshape(X_test_t.shape[0], chans, samples, kernels)
    
    
    if mod:
      blur_mix = 3/5
      X_train_addit, X_test_t, Y_train_addit, Y_test_t = train_test_split(X_test_t, Y_test_t, train_size=blur_mix, stratify=Y_test_t)

      X_train_t, Y_train_t =  np.concatenate((X_train_t, X_train_addit)), np.concatenate((Y_train_t, Y_train_addit))
    
    if i==0:
      X_train, X_test, Y_train, Y_test = X_train_t, X_test_t, Y_train_t, Y_test_t
    
    if i>=1:
      X_train, X_test, Y_train, Y_test = np.concatenate((X_train, X_train_t)), np.concatenate((X_test, X_test_t)), np.concatenate((Y_train, Y_train_t)), np.concatenate((Y_test, Y_test_t))


  X_train, X_validate, Y_train, Y_validate = train_test_split(X_train, Y_train, train_size=0.7, stratify=Y_train)

  if print_info:
    print('X_train shape:', X_train.shape)
    print('X_validate shape:', X_validate.shape)
    print('X_test shape:', X_test.shape)
    print(X_train.shape[0], 'train samples')
    print(X_validate.shape[0], 'validate samples')
    print(X_test.shape[0], 'test samples')
  #NUmber of Samples = 3072, Channels =50, Timestamps = 141, Kernel value = 1 
  #768*50*141*1
  if norm:
    X_train, X_validate, X_test = X_train/np.linalg.norm(X_train, axis=0, keepdims=True),X_validate/np.linalg.norm(X_validate, axis=0, keepdims=True),X_test/np.linalg.norm(X_test, keepdims=True, axis=0) #ADDED NORMALIZATION HERE
  if scale:
    X_train, X_validate, X_test = X_train*100000, X_validate*100000, X_test*100000  #added scaling
  return X_train, X_validate, X_test, Y_train, Y_validate, Y_test

#model-evaluation function
def evaluate_model(model, xtest, ytest, xval, yval, xtrain, ytrain):
  ytest = ytest.argmax(axis=-1)
  yval = yval.argmax(axis=-1)
  ytrain = ytrain.argmax(axis=-1)
  
  model.load_weights('/tmp/checkpoint.h5')
  preds_train = model.predict(xtrain).argmax(axis=-1)
  preds_val = model.predict(xval).argmax(axis=-1)
  acc_train = np.mean(preds_train == ytrain)
  acc_val = np.mean(preds_val == yval)

  print("Train Classification accuracy: %f " % (acc_train))
  print("Validation Classification accuracy: %f " % (acc_val))

  
  probs       = model.predict(xtest)
  preds       = probs.argmax(axis = -1)  
  acc_test         = np.mean(preds == ytest)
  pr, rec, fsc, sup = precision_recall_fscore_support(ytest, preds, average='binary')
  
  print("Test Classification accuracy: %f " % (acc_test))
  print("Test Classification precision: %f " % (pr))
  print("Test Classification recall: %f " % (rec))
  print("Test Classification f1score: %f " % (fsc))

  accuracies_of_version = [acc_train, acc_val, acc_test]
  return ytest, preds, accuracies_of_version


from sklearn.metrics import confusion_matrix
import seaborn as sns

#Generate the confusion matrix
def generate_confusion_matrix(ytest, preds, class_names=['animate','inanimate'], plot=True):
  cf_matrix = confusion_matrix(ytest, preds)


  if plot:
    ax = sns.heatmap(cf_matrix, annot=True, cmap='Blues')
    ax.set_title('Seaborn Confusion Matrix with labels\n\n');
    ax.set_xlabel('\nPredicted Values')
    ax.set_ylabel('Actual Values ');
    ## Ticket labels - List must be in alphabetical order
    ax.xaxis.set_ticklabels(class_names)
    ax.yaxis.set_ticklabels(class_names)
    ## Display the visualization of the Confusion Matrix.
    plt.show()

  return cf_matrix

def save_cf_matrix(cf_matrix, version_name):
  np.save(f'/content/drive/MyDrive/meg-classification-matrices/cf_matrix_{version_name}.npy', cf_matrix) 
  return f"Saved as cf_matrix_{version_name} at PATH : /content/drive/MyDrive/meg-classification-matrices/"

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import ks_2samp 
from tqdm import tqdm
from sklearn.ensemble import RandomForestClassifier as rfc
from sklearn.metrics import classification_report 

def visualise_results(train_sizes = [], accuracies=[[]]): 

  accuracies = np.array(accuracies)
  plt.title('Training Sizes vs Accuracies')
  plt.plot(train_sizes, accuracies[:, 0], label = "train accuracy")
  plt.plot(train_sizes, accuracies[:, 1], label = "validation accuracy")
  plt.plot(train_sizes, accuracies[:, 2], label = "test accuracy")
  plt.legend()
  plt.show()

def diff_cols(datax, datay):
  diff_data = []
  dimensions = datax.shape[1]
  threshold = 0.1
  flag = 0
  for dim in range(dimensions):
        statistic, pvalue = ks_2samp(
            datax[:, dim], 
            datay[:, dim]
        )
        if pvalue <= 0.05 and np.abs(statistic) > threshold:
            diff_data.append({'feature': dim, 'p': np.round(pvalue, 5), 'statistic': np.round(np.abs(statistic), 2)})
            flag = 1
          
    # Put the differences into a dataframe
  if flag == 0:
    print("No difference at all")
    return None
  else:
    diff_df = pd.DataFrame(diff_data).sort_values(by='statistic', ascending=False)
    return diff_df

def plot_diff_cols(subx=[], suby=[], focus_on='train', at_most_plot_disp = 6):

  
  if focus_on == 'train':

    datax,_, _, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    datay, _, _, _, _, _ = get_subject_data(suby, mod=True, print_info=False)

  elif focus_on =='validate':

    _, datax, _, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    _, datay,_, _, _, _ = get_subject_data(suby, mod=True, print_info=False)
  
  elif focus_on == 'test':

    _, _, datax, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    _, _, datay, _, _, _ = get_subject_data(suby, mod=True, print_info=False)
  
  datax = datax.reshape(datax.shape[0], -1)
  datay = datay.reshape(datay.shape[0], -1)

  diff_df = diff_cols(datax, datay)
  
  if type(diff_df) == type(None):
    return 
  fig, axes = plt.subplots(at_most_plot_disp)

  if at_most_plot_disp == 1:
    axi = diff_df.index[0]
    dim_no = diff_df['feature'][axi]
    axes.set_title(f"Statistic = {str(diff_df['statistic'][axi])}, p = {str(diff_df['p'][axi])}")

    axes.hist(datax[:, dim_no], bins=50, label=f'subjects : {"-".join(list(map(str, subx)))} dimension :{str(dim_no)} ')  #plotting 0th dimension
    axes.hist(datay[:, dim_no], bins=50, label=f'subjects : {"-".join(list(map(str, suby)))} dimension :{str(dim_no)} ')  #plotting 0th dimension
    axes.legend()
  
  else:
    c = 0
    for axi in tqdm(diff_df.index):
      dim_no = diff_df['feature'][axi]
      axes[c].set_title(f"Statistic = {str(diff_df['statistic'][axi])}, p = {str(diff_df['p'][axi])}")

      axes[c].hist(datax[:, dim_no], bins=50, label=f'subjects : {"-".join(list(map(str, subx)))} dimension :{str(dim_no)} ')  #plotting 0th dimension
      axes[c].hist(datay[:, dim_no], bins=50, label=f'subjects : {"-".join(list(map(str, suby)))} dimension : {str(dim_no)} ')  #plotting 0th dimension
      axes[c].legend()
      c += 1
      if c == at_most_plot_disp:
        break
  
  

  return diff_df

SAVE_DATAX = {-1:None, 'stored':None} 
SAVE_DATAY = {-1:None, 'stored':None}  
def ml_diff_verdict(subx=[], suby=[], focus_on='train', plot_cf_matrix=True):
  
  global SAVE_DATAX, SAVE_DATAY
  subx_id = 0
  suby_id = 1
  
  class_names = ["subx set", "suby set"]
  if focus_on == 'train':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      datax,_, _, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']

    if list(SAVE_DATAY.keys())[:-1] != suby:
      datay,_, _, _, _, _ = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']
    

  elif focus_on =='validate':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      _,datax, _, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']
    
    if list(SAVE_DATAY.keys())[:-1] != suby:
      _,datay, _, _, _, _ = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']

    
  
  elif focus_on == 'test':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      _,_, datax, _, _, _ = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']
    
    if list(SAVE_DATAY.keys())[:-1] != suby:
      _,_, datay, _, _, _ = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']
    
  
  SAVE_DATAX = {n:None for n in subx}
  SAVE_DATAX['stored'] = datax

  SAVE_DATAY = {n:None for n in suby}
  SAVE_DATAY['stored'] = datay

  datax = datax.reshape(datax.shape[0], -1)
  datax_label = np.full((datax.shape[0]), subx_id)
  
  datay = datay.reshape(datay.shape[0], -1)
  datay_label = np.full((datay.shape[0]), suby_id)

  X = np.concatenate([datax, datay], axis=0)
  Y = np.concatenate([datax_label, datay_label], axis=0)


  XTR, XTE, YTR, YTE = train_test_split(X, Y, train_size=0.7, stratify=Y)
  #dataset = np.random.shuffle(np.concatenate([X, Y], axis=-1))
  #X = dataset[:, :dataset.shape[1]-1]
  #Y = np.squeeze(dataset[:, dataset.shape[1]-1])

  classifier = rfc(random_state=0, n_estimators=100)
  classifier.fit(XTR, YTR)

  YPR = classifier.predict(XTE)
  cf_matrix = generate_confusion_matrix(YTE, YPR, class_names, plot=plot_cf_matrix)
  
  #print(classification_report(YTE, YPR))

  return cf_matrix
  
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from seaborn import scatterplot

def perplexity_determiner(labels):
  N = labels.shape[0]
  from math import log, exp
  perp = int(exp(-0.179 + 0.51*log(N)))
  
  return perp

def tsne_visualise(subx=[], suby=[], focus_on='train', skip_pca=False, hue_type='label', style_type='class', perp='auto', iter=300):

  global SAVE_DATAX, SAVE_DATAY
  subx_id = 0
  suby_id = 1
  
  class_names = ["subx set", "suby set"]
  if focus_on == 'train':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      datax,_, _, datax_class, _, _ = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']

    if list(SAVE_DATAY.keys())[:-1] != suby:
      datay,_, _, datay_class, _, _ = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']
    

  elif focus_on =='validate':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      _,datax, _, _, datax_class, _ = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']
    
    if list(SAVE_DATAY.keys())[:-1] != suby:
      _,datay, _, _, datay_class, _ = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']

    
  
  elif focus_on == 'test':
    if list(SAVE_DATAX.keys())[:-1] != subx:
      _,_, datax, _, _, datax_class = get_subject_data(subx, mod=True, print_info=False)
    else:
      datax = SAVE_DATAX['stored']
    
    if list(SAVE_DATAY.keys())[:-1] != suby:
      _,_, datay, _, _, datay_class = get_subject_data(suby, mod=True, print_info=False)
    else:
      datay = SAVE_DATAY['stored']
    
  
  SAVE_DATAX = {n:None for n in subx}
  SAVE_DATAX['stored'] = datax

  SAVE_DATAY = {n:None for n in suby}
  SAVE_DATAY['stored'] = datay

  datax = datax.reshape(datax.shape[0], -1)
  datax_label = np.full((datax.shape[0]), subx_id)
  datax_class = np.argmax(datax_class, axis=1)

  datay = datay.reshape(datay.shape[0], -1)
  datay_label = np.full((datay.shape[0]), suby_id)
  datay_class = np.argmax(datay_class, axis=1)

  X = np.concatenate([datax, datay], axis=0)
  Y = np.concatenate([datax_label, datay_label], axis=0)
  Y_class = np.concatenate([datax_class, datay_class], axis=0)

  pca_result = X
  if not(skip_pca):
    pca = PCA(n_components=50)#n_components=min(X.shape[0], X.shape[1])
    pca_result = pca.fit_transform(X)

  if perp == 'auto':
    perp = perplexity_determiner(Y_class)
  tsne = TSNE(n_components=2, verbose=1, perplexity=perp, n_iter=iter)
  tsne_result = tsne.fit_transform(pca_result)

  X = tsne_result
  #Y = np.concatenate([datax_label, datay_label], axis=0)

  dataset = pd.DataFrame({'feature_1':X[:,0], 'feature_2':X[:,1], 'label':Y, 'class':Y_class})
  
  fig, ax = plt.subplots()
  ax.set_ylim(-20,100)
  scatterplot(x="feature_1", y= "feature_2", data=dataset, hue=hue_type, style=style_type, ax=ax)
  #plt.scatter(datax[:, 0], datax[:,1])
  #plt.scatter(datay[:, 0], datay[:,1])





def visualise_results_acr(train_sizes, methods):

  print(methods)
  plot_count = len(methods.keys())
  for acs in methods.keys():
    methods[acs] = np.array(methods[acs], dtype=np.float16)
    

  fig, axes = plt.subplots(plot_count)

  c = 0
  for acs in methods.keys():
    axes[c].plot(train_sizes, methods[acs][:, 0], label = f"{acs} train accuracy")
    axes[c].plot(train_sizes, methods[acs][:, 1], label = f"{acs} test accuracy")
    axes[c].legend()
    c += 1
  

def do_all(versions, end_at='v6', method_name='tr_80-test_20-kl_32-f1_8-d_2-f2_16-dr_0.5'):

  print(f"Doing all versions according to :- {method_name}\n")
  trainsplit, testsplit, kl, f1, d, f2, dr = method_name.split('-')

  trainsplit = int(trainsplit.split('_')[1])
  testsplit = int(testsplit.split('_')[1])
  kl = int(kl.split('_')[1])
  f1 = int(f1.split("_")[1])
  d = int(d.split("_")[1])
  f2 = int(f2.split("_")[1])
  dr = float(dr.split("_")[1])

  chans, samples, kernels = 50, 141, 1 
  model = EEGNet(nb_classes = 2, Chans = chans, Samples = samples, 
               dropoutRate = dr, kernLength = kl, F1 = f1, D = d, F2 = f2, 
               dropoutType = 'Dropout')
  
  numParams    = model.count_params() 
  class_weights = {0:1, 1:1}

  train_sizes = []
  accuracies = []
  for v in versions :
    print(f"{v} doing starts!\n")

    checkpointer = ModelCheckpoint(filepath='/tmp/checkpoint.h5', verbose=1,
                               save_best_only=True)
    
    X_train, X_validate, X_test, Y_train, Y_validate, Y_test = get_subject_data(versions[v], mod=True)
    #undid this normalize upper line
    train_sizes.append(X_train.shape[0])

    model.compile(loss='categorical_crossentropy', optimizer='adam', 
                metrics = ['accuracy'])
      
    fittedModel = model.fit(X_train, Y_train, batch_size = 16, epochs = 100, #batch size inc to 32 
                          verbose = 2, validation_data=(X_validate, Y_validate),
                          callbacks=[checkpointer], class_weight = class_weights)

    ytest, preds, accuracies_of_version = evaluate_model(model, X_test, Y_test, X_validate, Y_validate, X_train, Y_train)
    cf_matrix = generate_confusion_matrix(ytest, preds)

    accuracies.append(accuracies_of_version)
    save_cf_matrix(cf_matrix, f'{v}_matrix')
    print(f"{v} doing ends!\n")
    if v == end_at:
      break
  visualise_results(train_sizes, accuracies)
  accuracies_mod = [[accuracies[sam][0], accuracies[sam][1]] for sam in range(len(accuracies))]
  return train_sizes, accuracies_mod

#type(EEGNet)

SAVE_DATAX = {-1:None, 'stored':None}
SAVE_DATAY = {-1:None, 'stored':None}
