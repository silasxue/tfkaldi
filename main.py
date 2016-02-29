from six.moves import configparser
import prepare_data
import os
import nnet
import kaldi_io
import cPickle as pickle
import gzip

TRAINFEATURES = True
TESTFEATURES = True
MONO_GMM = True
TEST_MONO = True
TRI_GMM = True
TEST_TRI = True
NNET = True
DECODE = True

#read config file
config = configparser.ConfigParser()
config.read('config/config_AURORA4.cfg')
current_dir = os.getcwd()

######################################################################################################
#compute the features of the training set
if TRAINFEATURES:
	feat_cfg = dict(config.items('features'))

	print('------- computing training features ----------')
	prepare_data.prepare_data(config.get('directories','train_data'), config.get('directories','train_features'),feat_cfg)
	
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	if config.get('features','kaldi_cmvn'):
		#compute the cmvn stats
		print('------- computing cmvn stats ----------')
		os.system('steps/compute_cmvn_stats.sh %s %s/cmvn %s' % (config.get('directories','train_features'), config.get('directories','expdir'), config.get('directories','train_features')))
	else:
		#create fake cmvn stats
		os.system('steps/compute_cmvn_stats.sh --fake %s %s/cmvn %s' % (config.get('directories','train_features'), config.get('directories','expdir'), config.get('directories','train_features')))
	
	#go back to working dir
	os.chdir(current_dir)
	
######################################################################################################
#compute the features of the testing set
if TESTFEATURES:
	feat_cfg = dict(config.items('features'))

	print('------- computing testing features ----------')
	prepare_data.prepare_data(config.get('directories','test_data'), config.get('directories','test_features'),feat_cfg)
	
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	if config.get('features','kaldi_cmvn'):
		#compute the cmvn stats
		print('------- computing cmvn stats ----------')
		os.system('steps/compute_cmvn_stats.sh %s %s/cmvn %s' % (config.get('directories','test_features'), config.get('directories','expdir'), config.get('directories','test_features')))
	else:
		#create fake cmvn stats
		os.system('steps/compute_cmvn_stats.sh --fake %s %s/cmvn %s' % (config.get('directories','test_features'), config.get('directories','expdir'), config.get('directories','test_features')))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################	
#use kaldi to train the monophone GMM
if MONO_GMM:
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))

	#train monophone GMM
	print('------- training monophone GMM ----------')
	os.system('steps/train_mono.sh --nj %s --cmd %s --config %s/config/mono.conf %s %s %s/%s' % (config.get('general','num_jobs'), config.get('mono_gmm','cmd'), current_dir, config.get('directories','train_features'), config.get('directories','language'), config.get('directories','expdir'), config.get('mono_gmm','name')))
	
	#build decoding graphs
	print('------- building decoding graphs ----------')
	os.system('utils/mkgraph.sh --mono %s %s/%s %s/%s/graph' % (config.get('directories','language_test_bg'), config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('mono_gmm','name')))
	
	#align the data
	print('------- aligning the data ----------')
	os.system('steps/align_si.sh --nj %s --cmd %s --config %s/config/ali_mono.conf %s %s %s/%s %s/%s/ali' % (config.get('general','num_jobs'), config.get('mono_gmm','cmd'), current_dir, config.get('directories','train_features'), config.get('directories','language'), config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('mono_gmm','name')))
	
	#convert alignments (transition-ids) to pdf-ids
	for i in range(int(config.get('general','num_jobs'))):
		print('gunzip -c %s/%s/ali/ali.%d.gz | ali-to-pdf %s/%s/ali/final.mdl ark:- ark,t:- | gzip >  %s/%s/ali/pdf.%d.gz' % (config.get('directories','expdir'), config.get('mono_gmm','name'), i+1, config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('mono_gmm','name'), i+1))
		os.system('gunzip -c %s/%s/ali/ali.%d.gz | ali-to-pdf %s/%s/ali/final.mdl ark:- ark,t:- | gzip >  %s/%s/ali/pdf.%d.gz' % (config.get('directories','expdir'), config.get('mono_gmm','name'), i+1, config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('mono_gmm','name'), i+1))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################	
#use kaldi to test the monophone gmm
if TEST_MONO:
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	#decode using kaldi
	print('------- testing monophone GMM ----------')
	os.system('steps/decode.sh --cmd %s --nj %s %s/%s/graph %s %s/%s/decode | tee %s/%s/decode.log || exit 1;' % (config.get('mono_gmm','cmd'), config.get('general','num_jobs'), config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','test_features'), config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('mono_gmm','name')))
	
	#get results
	os.system('grep WER %s/%s/decode/wer_* | utils/best_wer.sh' % (config.get('directories','expdir'), config.get('mono_gmm','name')))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################	
#use kaldi to train the triphone GMM
if TRI_GMM:
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	#train triphone GMM
	print('------- training triphone GMM ----------')
	os.system('steps/train_deltas.sh --cmd %s --config %s/config/tri.conf %s %s %s %s %s/%s/ali %s/%s' % (config.get('tri_gmm','cmd'), current_dir, config.get('tri_gmm','num_leaves'), config.get('tri_gmm','tot_gauss'), config.get('directories','train_features'), config.get('directories','language'), config.get('directories','expdir'), config.get('mono_gmm','name'), config.get('directories','expdir'), config.get('tri_gmm','name')))
	
	#build decoding graphs
	print('------- building decoding graphs ----------')
	os.system('utils/mkgraph.sh %s %s/%s %s/%s/graph' % (config.get('directories','language_test_bg'), config.get('directories','expdir'), config.get('tri_gmm','name'), config.get('directories','expdir'), config.get('tri_gmm','name')))
	
	#align the data
	print('------- aligning the data ----------')
	os.system('steps/align_si.sh --nj %s --cmd %s --config %s/config/ali_tri.conf %s %s %s/%s %s/%s/ali' % (config.get('general','num_jobs'), config.get('tri_gmm','cmd'), current_dir, config.get('directories','train_features'), config.get('directories','language'), config.get('directories','expdir'), config.get('tri_gmm','name'), config.get('directories','expdir'), config.get('tri_gmm','name')))
	
	#convert alignments (transition-ids) to pdf-ids
	for i in range(int(config.get('general','num_jobs'))):
		os.system('gunzip -c %s/%s/ali/ali.%d.gz | ali-to-pdf %s/%s/ali/final.mdl ark:- ark,t:- | gzip >  %s/%s/ali/pdf.%d.gz' % (config.get('directories','expdir'), config.get('tri_gmm','name'), i+1, config.get('directories','expdir'), config.get('tri_gmm','name'), config.get('directories','expdir'), config.get('tri_gmm','name'), i+1))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################
#use kaldi to test the triphone GMM
if TEST_TRI:
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	#decode using kaldi
	print('------- testing triphone GMM ----------')
	os.system('steps/decode.sh --cmd %s --nj %s %s/%s/graph %s %s/%s/decode | tee %s/%s/decode.log || exit 1;' % (config.get('tri_gmm','cmd'), config.get('general','num_jobs'), config.get('directories','expdir'), config.get('tri_gmm','name'), config.get('directories','test_features'), config.get('directories','expdir'), config.get('tri_gmm','name'), config.get('directories','expdir'), config.get('tri_gmm','name')))
	
	#get results
	os.system('grep WER %s/%s/decode/wer_* | utils/best_wer.sh' % (config.get('directories','expdir'), config.get('tri_gmm','name')))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################
#get nnet configs
nnet_cfg = dict(config.items('nnet'))

#define location to save neural nets
nnet_cfg['savedir'] = config.get('directories','expdir') + '/' + nnet_cfg['name']
if not os.path.isdir(nnet_cfg['savedir']):
	os.mkdir(nnet_cfg['savedir'])
if not os.path.isdir(nnet_cfg['savedir'] + '/validation'):
	os.mkdir(nnet_cfg['savedir'] + '/validation')
	
#define location to save decoding files
nnet_cfg['decodedir'] = nnet_cfg['savedir'] + '/decode'
if not os.path.isdir(nnet_cfg['decodedir']):
	os.mkdir(nnet_cfg['decodedir'])

#check which gmm model should be used
if nnet_cfg['monophone'] == 'True':
	gmm_name = config.get('mono_gmm','name')
else:
	gmm_name = config.get('tri_gmm','name')
	
#get the feature input dim
reader = kaldi_io.KaldiReadIn(config.get('directories','train_features') + '/feats.scp')
(_,features,_) = reader.read_next_utt()
nnet_cfg['input_dim'] = features.shape[1]
reader.close()

#get number of output labels
numpdfs = open(config.get('directories','expdir') + '/' + gmm_name + '/graph/num_pdfs')
num_labels = numpdfs.read()
nnet_cfg['num_labels'] = int(num_labels[0:len(num_labels)-1])
	
#create the neural net 	
Nnet = nnet.nnet(nnet_cfg)

if NNET:
	
	#if we are not at fina yet we will need the alignments
	if nnet_cfg['starting_step'][0:5] != 'final':
		#read the alignments
		print('------- reading alignments ----------')
		alignments = {}
		for i in range(int(config.get('general','num_jobs'))):
			alignments.update(kaldi_io.read_alignments(config.get('directories','expdir') + '/' + gmm_name + '/ali/pdf.' + str(i+1) + '.gz'))

	#initialize the neural net
	if nnet_cfg['starting_step'] == '-1':	
	
		#shuffle the examples on disk
		print('------- shuffling examples ----------')
		prepare_data.shuffle_examples(config.get('directories','train_features'), int(nnet_cfg['valid_size']))
	
		#initlialize the neural net
		print('------- initializing neural net ----------')
		Nnet.graphop('init', {'featdir':config.get('directories','train_features'), 'alignments':alignments})
	
	if nnet_cfg['starting_step'][0:5] != 'final':		
		#train the neural net		
		print('------- training neural net ----------')
		Nnet.graphop('train', {'featdir':config.get('directories','train_features'), 'alignments':alignments})
	
	if nnet_cfg['starting_step'] != 'final-prio':
		#compute the state prior probabilities
		print('------- computing state priors ----------')
		Nnet.graphop('prior', {'featdir':config.get('directories','train_features')})
		
	#create a dumy neural net
	print('------- creating dummy nnet ----------')
	kaldi_io.create_dummy('%s/%s' % (config.get('directories','expdir'), gmm_name), nnet_cfg['decodedir'], config.get('directories','test_features'), nnet_cfg['num_labels'])
	
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	#build decoding graphs
	print('------- building decoding graphs ----------')
	if nnet_cfg['monophone'] == 'True':
		os.system('utils/mkgraph.sh --mono %s %s %s/graph' % (config.get('directories','language_test_bg'), nnet_cfg['decodedir'], nnet_cfg['decodedir']))
	else:
		os.system('utils/mkgraph.sh %s %s %s/graph' % (config.get('directories','language_test_bg'), nnet_cfg['decodedir'], nnet_cfg['decodedir']))
	
	#go back to working dir
	os.chdir(current_dir)

######################################################################################################		
if DECODE:
	#use the neural net to calculate posteriors for the testing set
	print('------- computing state pseudo-likelihoods ----------')
	Nnet.graphop('decode', {'featdir':config.get('directories','test_features')})
	
	#change directory to kaldi egs
	os.chdir(config.get('directories','kaldi_egs'))
	
	#create fake cmvn stats
	os.system('steps/compute_cmvn_stats.sh --fake %s %s/cmvn %s' % (nnet_cfg['decodedir'], config.get('directories','expdir'), nnet_cfg['decodedir']))
	
	#decode using kaldi
	print('------- decoding testing sets ----------')
	os.system('steps/nnet2/decode.sh --cmd %s --nj %s %s/graph %s %s/kaldi_decode | tee %s/decode.log || exit 1;' % (nnet_cfg['cmd'], config.get('general','num_jobs'), nnet_cfg['decodedir'], nnet_cfg['decodedir'], nnet_cfg['decodedir'], nnet_cfg['decodedir']))
	
	#get results
	os.system('grep WER %s/kaldi_decode/wer_* | utils/best_wer.sh' % nnet_cfg['decodedir'])
	
	#go back to working dir
	os.chdir(current_dir)
	
	
	
	
	
