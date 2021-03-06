# Multimodal Motion Prediction based on Sampling WTA+CGF in Pytorch
Use WTA loss with Clustering and Gaussian Fitting (WTA+CGF) to do multimodal motion prediction.

This is a repository presenting multimodal motion prediction with multiple hypothesis estimation with the Clustering and Gaussian Fitting (CGF) method.

#### Requirements
- pytorch
- matplotlib 

#### Data
Two evaluation sets are provided. <br />
Eval 1: [Synthetic] Single-object Interaction Dataset ([SID](https://github.com/Woodenonez/MultimodalMotionPred_SamplingWTACGF_Pytorch/blob/main/src/data_handle/sid_object.py)). <br />
Eval 2: [Realworld] Stanford Drone Dataset ([SDD](https://cvgl.stanford.edu/projects/uav_data/)) ***GO TO BRANCH "sdd_test"***.

#### Model
The model is pre-trained.

#### Test run
All 'main' files are meant to be run. The 'evaluation' file shows the evaluation result. The 'test' file shows a visualized result.
