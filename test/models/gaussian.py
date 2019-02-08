import dgm
import numpy as np
import torch
import torch.nn as nn


class Prior(nn.Module):
    def __init__(self, init_mean, std):
        super(Prior, self).__init__()
        self.mean = nn.Parameter(torch.tensor(init_mean, dtype=torch.float))
        self.std = torch.tensor(std, dtype=torch.float)

    def forward(self):
        return torch.distributions.Normal(loc=self.mean, scale=self.std)


class Likelihood(nn.Module):
    def __init__(self, init_std):
        super(Likelihood, self).__init__()
        self.log_std = nn.Parameter(
            torch.log(torch.tensor(init_std, dtype=torch.float)))

    def forward(self, latent=None, time=None):
        return torch.distributions.Normal(
            loc=latent, scale=torch.exp(self.log_std))


class InferenceNetwork(nn.Module):
    def __init__(self, init_mult, init_bias, init_std):
        super(InferenceNetwork, self).__init__()
        self.mult = nn.Parameter(torch.tensor(init_mult, dtype=torch.float))
        self.bias = nn.Parameter(torch.tensor(init_bias, dtype=torch.float))
        self.log_std = nn.Parameter(
            torch.log(torch.tensor(init_std, dtype=torch.float)))

    def forward(self, previous_latent=None, time=None, observations=None):
        return torch.distributions.Normal(
            loc=self.mult * observations[0] + self.bias,
            scale=torch.exp(self.log_std))


def get_proposal_params(prior_mean, prior_std, obs_std):
    posterior_var = 1 / (1 / prior_std**2 + 1 / obs_std**2)
    posterior_std = np.sqrt(posterior_var)
    multiplier = posterior_var / obs_std**2
    offset = posterior_var * prior_mean / prior_std**2

    return multiplier, offset, posterior_std


class TrainingStats(object):
    def __init__(self, logging_interval=100):
        self.prior_mean_history = []
        self.obs_std_history = []
        self.q_mult_history = []
        self.q_bias_history = []
        self.q_std_history = []
        self.iteration_idx_history = []
        self.elbo_history = []
        self.logging_interval = logging_interval

    def __call__(self, epoch_idx, epoch_iteration_idx, elbo, loss, autoencoder):
        self.prior_mean_history.append(autoencoder.initial.mean.item())
        self.obs_std_history.append(
            torch.exp(autoencoder.emission.log_std).item()
        )
        self.q_mult_history.append(autoencoder.proposal.mult.item())
        self.q_bias_history.append(autoencoder.proposal.bias.item())
        self.q_std_history.append(
            torch.exp(autoencoder.proposal.log_std).item()
        )
        elbo = torch.mean(elbo)
        self.elbo_history.append(float(elbo.data.numpy()))

        self.iteration_idx_history.append(epoch_iteration_idx)
        if epoch_iteration_idx % self.logging_interval == 0:
            print('Iteration: {} - Elbo: {}'.format(epoch_iteration_idx, torch.mean(elbo)))
