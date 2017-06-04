from __future__ import division
from __future__ import print_function

import logging
import os
from datetime import datetime
import tensorflow as tf
import numpy as np
from speeddet import *
from util import get_minibatches, Progbar
from play import *

tf.app.flags.DEFINE_integer("epochs", 10, "Number of epochs to train.")
tf.app.flags.DEFINE_integer("batch_size", 16, "Batch size to use during training.")
tf.app.flags.DEFINE_integer("print_every", 100, "How many iterations to do per print.")
tf.app.flags.DEFINE_string("train_dir", "../scratch", "Training directory to save the model parameters (default: ../scratch).")
FLAGS = tf.app.flags.FLAGS

def leaky_relu(x, alpha=0.01):
    """Compute the leaky ReLU activation function.

    Inputs:
    - x: TensorFlow Tensor with arbitrary shape
    - alpha: leak parameter for leaky ReLU

    Returns:
    TensorFlow Tensor with the same shape as x
    """
    return tf.maximum(alpha * x, x)

def baseline(X, is_training):
    conv1_out = tf.layers.conv2d(inputs=X, filters=32, kernel_size=[5, 5], activation=tf.nn.relu)
    bn1_out = tf.layers.batch_normalization(conv1_out, training=is_training)
    pool1_out = tf.layers.max_pooling2d(inputs=bn1_out, pool_size=[4, 4], strides=4)

    conv2_out = tf.layers.conv2d(inputs=pool1_out, filters=32, kernel_size=[5, 5], activation=tf.nn.relu)
    bn2_out = tf.layers.batch_normalization(conv2_out, training=is_training)
    pool2_out = tf.layers.max_pooling2d(inputs=bn2_out, pool_size=[4, 4], strides=4)

    return pool2_out

def res_block(X, num_filters, is_training, downsample=False):
    stride = 1
    if downsample:
        stride = 2
        num_filters *= 2
    conv1 = tf.layers.conv2d(X, num_filters, 3, strides=stride, padding='same', activation=tf.nn.relu)
    bn1 = tf.layers.batch_normalization(conv1, training=is_training)
    conv2 = tf.layers.conv2d(bn1, num_filters, 3, padding='same', activation=tf.nn.relu)
    bn2 = tf.layers.batch_normalization(conv2, training=is_training)
    if downsample:
        X = tf.layers.average_pooling2d(X, stride, stride, padding='same')
        X = tf.pad(X, [[0,0], [0,0], [0,0], [num_filters // 4, num_filters // 4]])
    return bn2 + X

def res_net(X, is_training):
    init_out = tf.layers.conv2d(X, 64, 7, strides=2, activation=tf.nn.relu)
    layer_in = tf.layers.batch_normalization(init_out, training=is_training)
    for i in range(2):
        out = res_block(layer_in, 64, is_training)
        layer_in = out
    num_filters = [64, 128, 256]
    block_in = out
    for num_filter in num_filters:
        layer_1 = res_block(block_in, num_filter, is_training, downsample=True)
        layer_2 = res_block(layer_1, 2 * num_filter, is_training)
        block_in = layer_2
    return layer_2

class ConvModel(object):
    def __init__(self, options):
        """
        Initializes your System

        :param encoder: an encoder that you constructed in train.py
        :param decoder: a decoder that you constructed in train.py
        :param args: pass in more arguments as needed
        """

        # ==== set up training/updating procedure ====
        # implement learning rate annealing
        self.lr = 1e-3
        # lr = tf.train.exponential_decay(FLAGS.learning_rate, global_step, FLAGS.decay_step, FLAGS.decay_rate,
        #                                 staircase=True)
        self.session = tf.Session()
        self.options = options

    def close(self):
        self.session.close()

    # def setup_placeholders(self, X_train):
    def setup_placeholders(self, **options):
        tp = tf.float32
        H,W,C = options['inputshape']
        self.X_placeholder = tf.placeholder(tp, [None, H, W, C])
        self.y_placeholder = tf.placeholder(tp, [None,1])
        self.is_training = tf.placeholder(tf.bool)

    def setup_network(self, X, y, is_training):
        print("\n\n===== Setup Network ======\n\n")

        if self.options['convmode'] == 0:
            baseline_out = baseline(X, is_training)
            flat_dim = np.product(baseline_out.shape[1:]).value
            baseline_out_flat = tf.reshape(baseline_out, [-1, flat_dim])

            affine1_out = tf.layers.dense(inputs=baseline_out_flat, units=1024, activation=tf.nn.relu)
            bn3_out = tf.layers.batch_normalization(affine1_out, training=is_training)
            dropout1_out = tf.layers.dropout(inputs=bn3_out, rate=0.4, training=is_training)

            affine2_out = tf.layers.dense(inputs=dropout1_out, units=512, activation=tf.nn.relu)
            bn4_out = tf.layers.batch_normalization(affine2_out, training=is_training)
            conv_out = tf.layers.dropout(inputs=bn4_out, rate=0.4, training=is_training)

        elif self.options['convmode'] == 1:
            res_out = res_net(X, is_training)
            flat_dim = np.product(res_out.shape[1:]).value
            conv_out = tf.reshape(res_out, [-1, flat_dim])

        out_dim = np.product(y.shape[1:]).value
        affine3_out = tf.layers.dense(inputs=conv_out, units=out_dim)
        return affine3_out

    def setup_system(self):
        """
        After your modularized implementation of encoder and decoder
        you should call various functions inside encoder, decoder here
        to assemble your reading comprehension system!
        :param qn_embeddings: embedding of question words, of size (batch_size, embedding_size)
        :param con_embeddings: embedding of context words, of size (batch_size, embedding_size)
        :self.start_pred & self.end_pred: tensors of shape [batch_size, FLAGS.con_max_len]
                                          a probability distribution over context
        """

        cpu = self.options['cpu']
        if cpu:
            with tf.device('\cpu:0'):
                self.pred = self.setup_network(self.X_placeholder, self.y_placeholder, self.is_training)
        else:
            self.pred = self.setup_network(self.X_placeholder, self.y_placeholder, self.is_training)

    def setup_loss(self):
        """
        Set up your loss computation here
        :return:
        """
        self.loss = tf.nn.l2_loss(self.pred - self.y_placeholder)

    def create_feed_dict(self, X, y, is_training=False):
        """
        Create a feed_dict
        :params: all are tensors of size [batch_size, ]
        :return: the feed_dict
        """

        feed_dict = {}
        feed_dict[self.X_placeholder] = X
        feed_dict[self.y_placeholder] = y
        feed_dict[self.is_training] = is_training

        return feed_dict

    def optimize(self, X_train, y_train):
        """
        Takes in actual data to optimize your model
        This method is equivalent to a step() function
        :param
        :return loss: training loss
        """
        # construct feed_dict
        input_feed = self.create_feed_dict(X_train, y_train, True)

        output_feed = [self.train_step, self.loss]

        _, loss = self.session.run(output_feed, feed_dict=input_feed)

        return loss

    def test(self, qns, mask_qns, cons, mask_cons, labels):
        """
        in here you should compute a cost for your validation set
        and tune your hyperparameters according to the validation set performance
        :param
        :return loss: validation loss for this batch
        """
        pass

        # TODO

    def validate(self, X_val, y_val):
        """
        Iterate through the validation dataset and determine what
        the validation cost is.

        This method calls self.test() which explicitly calculates validation cost.

        How you implement this function is dependent on how you design
        your data iteration function

        :param
        :return: validation cost of the batch
        """

        # compute loss for every single example and add together
        input_feed = self.create_feed_dict(X_val, y_val)

        output_feed = self.loss

        loss = self.session.run(output_feed, feed_dict=input_feed)

        return loss

    def run_epoch(self, frameTrain, frameVal):
        """
        Run 1 epoch. Train on training examples, evaluate on validation set.
        """
        options = self.options
        path = options['path']
        train_losses = []
        numTrain = frameTrain.shape[0]
        prog = Progbar(target=1 + int(numTrain / FLAGS.batch_size))
        for i, frameBatch in enumerate(get_minibatches(frameTrain, FLAGS.batch_size)):
            batch = loadData(frameBatch, **options)
            loss = self.optimize(*batch)
            train_losses.append(loss)
            if (self.global_step % FLAGS.print_every) == 0:
                logging.info("Iteration {0}: with minibatch training l2_loss = {1:.3g} and mse of {2:.2g}"\
                      .format(self.global_step, loss, loss/FLAGS.batch_size))
            prog.update(i + 1, [("train loss", loss)])
        total_train_mse = np.sum(train_losses)/numTrain

        print('')
        val_losses = []
        numVal = frameVal.shape[0]
        prog = Progbar(target=1 + int(numVal / FLAGS.batch_size))
        for i, frameBatch in enumerate(get_minibatches(frameVal, FLAGS.batch_size)):
            batch = loadData(frameBatch, **options)
            loss = self.validate(*batch)
            val_losses.append(loss)
            prog.update(i + 1, [("validation loss", loss)])
        print('')
        total_val_mse = np.sum(val_losses)/numVal
        return total_train_mse, train_losses, total_val_mse, val_losses

    def train(self, frameTrain, frameVal):
        """
        Implement main training loop

        :param
        :return:
        """

        plot_losses = self.options['plot_losses']

        self.setup_placeholders(**self.options)
        self.setup_system()
        self.setup_loss()
        self.saver = tf.train.Saver(max_to_keep=50)

        # print number of parameters
        params = tf.trainable_variables()
        num_params = sum(map(lambda t: np.prod(tf.shape(t.value()).eval(session=self.session)), params))
        logging.info("Number of params: %d" % num_params)

        # batch normalization in tensorflow requires this extra dependency
        extra_update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        with tf.control_dependencies(extra_update_ops):
            self.global_step = tf.Variable(0, trainable=False)
            optimizer = tf.train.AdamOptimizer(self.lr)
            grad_and_vars = optimizer.compute_gradients(self.loss)
            self.train_step = optimizer.apply_gradients(grad_and_vars, global_step=self.global_step)

        self.session.run(tf.global_variables_initializer())
        # y_train = np.reshape(vly_train, (-1, 1))
        # y_val = np.reshape(vly_val, (-1, 1))
        # training
        for epoch in range(FLAGS.epochs):
            logging.info("Epoch %d out of %d", epoch+1, FLAGS.epochs)
            total_train_mse, train_losses, total_val_mse, val_losses = \
                self.run_epoch(frameTrain, frameVal)
            logging.info("Epoch {2}, Overall train mse = {0:.4g}, Overall val mse = {1:.4g}\n"\
                  .format(total_train_mse, total_val_mse, epoch))
            if plot_losses:
                plt.plot(train_losses)
                plt.plot(val_losses)
                plt.grid(True)
                plt.title('Epoch {} Loss'.format(e+1))
                plt.xlabel('minibatch number')
                plt.ylabel('minibatch loss')
                plt.show()
        # save model weights
        # model_path = FLAGS.train_dir + "/convmodel_{:%Y%m%d_%H%M%S}_speedmode_{}/".format(datetime.now(), self.options['speedmode'])
        model_path = FLAGS.train_dir + "/convmodel_speedmode_{}/".format(datetime.now(), self.options['speedmode'])
        if not os.path.exists(model_path):
            os.makedirs(model_path)
        logging.info("Saving model parameters...")
        self.saver.save(self.session, model_path + "model.weights")
        # return (total_val_mse, 0, 0, 0)