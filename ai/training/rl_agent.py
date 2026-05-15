"""
JARVIS AI Trading OS - Reinforcement Learning Trading Agent

Implements DQN and PPO agents with a gym-like TradingEnvironment.
"""

from __future__ import annotations

import logging
import random
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Optional, Sequence

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from torch.distributions import Categorical
except ImportError:
    raise ImportError("PyTorch is required: pip install torch")

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

class Action(IntEnum):
    BUY = 0
    SELL = 1
    HOLD = 2
    CLOSE = 3


@dataclass
class EnvironmentConfig:
    initial_balance: float = 10_000.0
    commission: float = 0.0002
    max_position: float = 1.0
    leverage: float = 1.0
    risk_free_rate: float = 0.0
    episode_length: Optional[int] = None
    reward_scaling: float = 1.0


@dataclass
class StepResult:
    observation: np.ndarray
    reward: float
    done: bool
    info: dict[str, Any]


class TradingEnvironment:
    """
    Gym-like trading environment.

    State vector: OHLCV data + technical indicators + position info.
    Actions: BUY, SELL, HOLD, CLOSE.
    Reward: risk-adjusted PnL.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        config: Optional[EnvironmentConfig] = None,
        indicator_columns: Optional[list[str]] = None,
    ) -> None:
        self.config = config or EnvironmentConfig()
        self._raw = data.copy().reset_index(drop=True)
        self._ohlcv = ["open", "high", "low", "close", "volume"]
        self._indicator_cols = indicator_columns or []
        self._feature_cols = self._ohlcv + self._indicator_cols

        for col in self._ohlcv:
            if col not in self._raw.columns:
                if col == "volume":
                    self._raw["volume"] = 0.0
                else:
                    raise ValueError(f"Missing column: {col}")

        self._current_step = 0
        self._balance = self.config.initial_balance
        self._position = 0.0
        self._entry_price = 0.0
        self._total_pnl = 0.0
        self._trade_count = 0
        self._returns: list[float] = []
        self._done = False

    @property
    def observation_size(self) -> int:
        return len(self._feature_cols) + 3  # + position, unrealized_pnl, balance_pct

    @property
    def action_size(self) -> int:
        return len(Action)

    def reset(self) -> np.ndarray:
        self._current_step = 0
        self._balance = self.config.initial_balance
        self._position = 0.0
        self._entry_price = 0.0
        self._total_pnl = 0.0
        self._trade_count = 0
        self._returns = []
        self._done = False
        return self._get_observation()

    def step(self, action: int) -> StepResult:
        if self._done:
            raise RuntimeError("Episode is done; call reset()")

        act = Action(action)
        price = float(self._raw.loc[self._current_step, "close"])
        reward = 0.0
        trade_pnl = 0.0

        if act == Action.BUY and self._position <= 0:
            if self._position < 0:
                trade_pnl = self._close_position(price)
            self._position = self.config.max_position
            self._entry_price = price
            self._trade_count += 1

        elif act == Action.SELL and self._position >= 0:
            if self._position > 0:
                trade_pnl = self._close_position(price)
            self._position = -self.config.max_position
            self._entry_price = price
            self._trade_count += 1

        elif act == Action.CLOSE and self._position != 0:
            trade_pnl = self._close_position(price)

        unrealized = self._unrealized_pnl(price)
        reward = (trade_pnl + unrealized * 0.01) * self.config.reward_scaling
        if trade_pnl != 0:
            self._returns.append(trade_pnl)

        self._current_step += 1
        ep_len = self.config.episode_length or len(self._raw)
        if self._current_step >= min(ep_len, len(self._raw)) - 1:
            if self._position != 0:
                final_price = float(self._raw.loc[self._current_step, "close"])
                self._close_position(final_price)
            self._done = True

        obs = self._get_observation()
        info = {
            "balance": self._balance,
            "position": self._position,
            "total_pnl": self._total_pnl,
            "trade_count": self._trade_count,
            "sharpe": self._sharpe_ratio(),
        }
        return StepResult(observation=obs, reward=reward, done=self._done, info=info)

    def _get_observation(self) -> np.ndarray:
        row = self._raw.loc[self._current_step, self._feature_cols].values.astype(np.float32)
        price = float(self._raw.loc[self._current_step, "close"])
        extra = np.array([
            self._position,
            self._unrealized_pnl(price) / self.config.initial_balance,
            self._balance / self.config.initial_balance,
        ], dtype=np.float32)
        return np.concatenate([row, extra])

    def _close_position(self, price: float) -> float:
        if self._position == 0:
            return 0.0
        pnl = (price - self._entry_price) * self._position
        pnl -= abs(pnl) * self.config.commission
        self._balance += pnl
        self._total_pnl += pnl
        self._position = 0.0
        self._entry_price = 0.0
        return pnl

    def _unrealized_pnl(self, current_price: float) -> float:
        if self._position == 0:
            return 0.0
        return (current_price - self._entry_price) * self._position

    def _sharpe_ratio(self) -> float:
        if len(self._returns) < 2:
            return 0.0
        arr = np.array(self._returns)
        std = arr.std()
        if std == 0:
            return 0.0
        return float((arr.mean() - self.config.risk_free_rate) / std * np.sqrt(252))


# ---------------------------------------------------------------------------
# Neural Network building blocks
# ---------------------------------------------------------------------------

class QNetwork(nn.Module):
    def __init__(self, state_size: int, action_size: int, hidden_sizes: Sequence[int] = (128, 64)) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        prev = state_size
        for h in hidden_sizes:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.ReLU())
            prev = h
        layers.append(nn.Linear(prev, action_size))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class ActorCritic(nn.Module):
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128) -> None:
        super().__init__()
        self.shared = nn.Sequential(
            nn.Linear(state_size, hidden_size),
            nn.ReLU(),
        )
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, action_size),
        )
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        shared = self.shared(x)
        return self.actor(shared), self.critic(shared)

    def act(self, state: torch.Tensor) -> tuple[int, torch.Tensor, torch.Tensor]:
        logits, value = self.forward(state)
        dist = Categorical(logits=logits)
        action = dist.sample()
        return int(action.item()), dist.log_prob(action), value


# ---------------------------------------------------------------------------
# Experience replay
# ---------------------------------------------------------------------------

@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    def __init__(self, capacity: int = 100_000) -> None:
        self._buffer: deque[Transition] = deque(maxlen=capacity)

    def push(self, transition: Transition) -> None:
        self._buffer.append(transition)

    def sample(self, batch_size: int) -> list[Transition]:
        return random.sample(list(self._buffer), min(batch_size, len(self._buffer)))

    def __len__(self) -> int:
        return len(self._buffer)


# ---------------------------------------------------------------------------
# DQN Agent
# ---------------------------------------------------------------------------

@dataclass
class DQNConfig:
    hidden_sizes: tuple[int, ...] = (128, 64)
    lr: float = 1e-3
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: float = 0.995
    batch_size: int = 64
    buffer_size: int = 100_000
    target_update_freq: int = 10
    max_episodes: int = 500
    device: str = "cpu"


class DQNAgent:
    """Deep Q-Network agent with experience replay and target network."""

    def __init__(self, env: TradingEnvironment, config: Optional[DQNConfig] = None) -> None:
        self.env = env
        self.config = config or DQNConfig()
        self.device = torch.device(self.config.device)

        state_size = env.observation_size
        action_size = env.action_size

        self.policy_net = QNetwork(state_size, action_size, self.config.hidden_sizes).to(self.device)
        self.target_net = QNetwork(state_size, action_size, self.config.hidden_sizes).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=self.config.lr)
        self.buffer = ReplayBuffer(self.config.buffer_size)
        self.epsilon = self.config.epsilon_start

        self._episode_rewards: list[float] = []

    def select_action(self, state: np.ndarray) -> int:
        if random.random() < self.epsilon:
            return random.randrange(self.env.action_size)
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(s)
            return int(q_values.argmax(dim=1).item())

    def _update(self) -> Optional[float]:
        if len(self.buffer) < self.config.batch_size:
            return None

        batch = self.buffer.sample(self.config.batch_size)
        states = torch.FloatTensor(np.array([t.state for t in batch])).to(self.device)
        actions = torch.LongTensor([t.action for t in batch]).unsqueeze(1).to(self.device)
        rewards = torch.FloatTensor([t.reward for t in batch]).to(self.device)
        next_states = torch.FloatTensor(np.array([t.next_state for t in batch])).to(self.device)
        dones = torch.FloatTensor([float(t.done) for t in batch]).to(self.device)

        q_values = self.policy_net(states).gather(1, actions).squeeze(1)
        with torch.no_grad():
            next_q = self.target_net(next_states).max(dim=1).values
            target = rewards + self.config.gamma * next_q * (1 - dones)

        loss = F.smooth_l1_loss(q_values, target)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        return float(loss.item())

    def train(self, num_episodes: Optional[int] = None) -> list[float]:
        episodes = num_episodes or self.config.max_episodes
        rewards_history: list[float] = []

        for ep in range(episodes):
            state = self.env.reset()
            total_reward = 0.0
            done = False

            while not done:
                action = self.select_action(state)
                result = self.env.step(action)
                self.buffer.push(Transition(
                    state=state,
                    action=action,
                    reward=result.reward,
                    next_state=result.observation,
                    done=result.done,
                ))
                self._update()
                state = result.observation
                total_reward += result.reward
                done = result.done

            self.epsilon = max(self.config.epsilon_end, self.epsilon * self.config.epsilon_decay)

            if (ep + 1) % self.config.target_update_freq == 0:
                self.target_net.load_state_dict(self.policy_net.state_dict())

            rewards_history.append(total_reward)
            self._episode_rewards.append(total_reward)

            if (ep + 1) % 50 == 0:
                avg = np.mean(rewards_history[-50:])
                logger.info("DQN Episode %d/%d | Reward=%.2f | Avg50=%.2f | Eps=%.3f",
                            ep + 1, episodes, total_reward, avg, self.epsilon)

        return rewards_history

    def predict(self, state: np.ndarray) -> int:
        with torch.no_grad():
            s = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            return int(self.policy_net(s).argmax(dim=1).item())

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "policy_state_dict": self.policy_net.state_dict(),
            "target_state_dict": self.target_net.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "episode_rewards": self._episode_rewards,
        }, str(path))
        logger.info("DQN model saved to %s", path)

    def load(self, path: str | Path) -> None:
        checkpoint = torch.load(str(path), map_location=self.device)
        self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
        self.target_net.load_state_dict(checkpoint["target_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.epsilon = checkpoint.get("epsilon", self.config.epsilon_end)
        self._episode_rewards = checkpoint.get("episode_rewards", [])
        logger.info("DQN model loaded from %s", path)

    @property
    def episode_rewards(self) -> list[float]:
        return list(self._episode_rewards)


# ---------------------------------------------------------------------------
# PPO Agent
# ---------------------------------------------------------------------------

@dataclass
class PPOConfig:
    hidden_size: int = 128
    lr: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    entropy_coef: float = 0.01
    value_coef: float = 0.5
    max_grad_norm: float = 0.5
    update_epochs: int = 4
    batch_size: int = 64
    rollout_length: int = 256
    max_episodes: int = 500
    device: str = "cpu"


class PPOAgent:
    """Proximal Policy Optimization agent with Actor-Critic and GAE."""

    def __init__(self, env: TradingEnvironment, config: Optional[PPOConfig] = None) -> None:
        self.env = env
        self.config = config or PPOConfig()
        self.device = torch.device(self.config.device)

        state_size = env.observation_size
        action_size = env.action_size

        self.model = ActorCritic(state_size, action_size, self.config.hidden_size).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.config.lr)

        self._episode_rewards: list[float] = []

    def _compute_gae(
        self,
        rewards: list[float],
        values: list[float],
        dones: list[bool],
        next_value: float,
    ) -> tuple[list[float], list[float]]:
        advantages: list[float] = []
        gae = 0.0
        values_ext = values + [next_value]

        for t in reversed(range(len(rewards))):
            mask = 0.0 if dones[t] else 1.0
            delta = rewards[t] + self.config.gamma * values_ext[t + 1] * mask - values_ext[t]
            gae = delta + self.config.gamma * self.config.gae_lambda * mask * gae
            advantages.insert(0, gae)

        returns = [a + v for a, v in zip(advantages, values)]
        return advantages, returns

    def train(self, num_episodes: Optional[int] = None) -> list[float]:
        episodes = num_episodes or self.config.max_episodes
        rewards_history: list[float] = []

        for ep in range(episodes):
            state = self.env.reset()
            done = False
            total_reward = 0.0

            states_buf: list[np.ndarray] = []
            actions_buf: list[int] = []
            log_probs_buf: list[torch.Tensor] = []
            rewards_buf: list[float] = []
            values_buf: list[float] = []
            dones_buf: list[bool] = []

            while not done:
                state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                action, log_prob, value = self.model.act(state_t)

                result = self.env.step(action)

                states_buf.append(state)
                actions_buf.append(action)
                log_probs_buf.append(log_prob.detach())
                rewards_buf.append(result.reward)
                values_buf.append(float(value.item()))
                dones_buf.append(result.done)

                state = result.observation
                total_reward += result.reward
                done = result.done

                if len(states_buf) >= self.config.rollout_length or done:
                    with torch.no_grad():
                        next_state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                        _, next_val = self.model(next_state_t)
                        next_value = float(next_val.item())

                    advantages, returns = self._compute_gae(
                        rewards_buf, values_buf, dones_buf, next_value,
                    )
                    self._ppo_update(states_buf, actions_buf, log_probs_buf, advantages, returns)

                    states_buf.clear()
                    actions_buf.clear()
                    log_probs_buf.clear()
                    rewards_buf.clear()
                    values_buf.clear()
                    dones_buf.clear()

            rewards_history.append(total_reward)
            self._episode_rewards.append(total_reward)

            if (ep + 1) % 50 == 0:
                avg = np.mean(rewards_history[-50:])
                logger.info("PPO Episode %d/%d | Reward=%.2f | Avg50=%.2f",
                            ep + 1, episodes, total_reward, avg)

        return rewards_history

    def _ppo_update(
        self,
        states: list[np.ndarray],
        actions: list[int],
        old_log_probs: list[torch.Tensor],
        advantages: list[float],
        returns: list[float],
    ) -> None:
        states_t = torch.FloatTensor(np.array(states)).to(self.device)
        actions_t = torch.LongTensor(actions).to(self.device)
        old_lp_t = torch.stack(old_log_probs).to(self.device)
        adv_t = torch.FloatTensor(advantages).to(self.device)
        ret_t = torch.FloatTensor(returns).to(self.device)

        adv_std = adv_t.std()
        if adv_std > 0:
            adv_t = (adv_t - adv_t.mean()) / (adv_std + 1e-8)

        dataset_size = len(states)
        for _ in range(self.config.update_epochs):
            indices = torch.randperm(dataset_size)
            for start in range(0, dataset_size, self.config.batch_size):
                end = start + self.config.batch_size
                idx = indices[start:end]

                logits, values = self.model(states_t[idx])
                dist = Categorical(logits=logits)
                new_log_probs = dist.log_prob(actions_t[idx])
                entropy = dist.entropy().mean()

                ratio = (new_log_probs - old_lp_t[idx]).exp()
                surr1 = ratio * adv_t[idx]
                surr2 = torch.clamp(ratio, 1 - self.config.clip_epsilon, 1 + self.config.clip_epsilon) * adv_t[idx]
                policy_loss = -torch.min(surr1, surr2).mean()
                value_loss = F.mse_loss(values.squeeze(-1), ret_t[idx])
                loss = policy_loss + self.config.value_coef * value_loss - self.config.entropy_coef * entropy

                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
                self.optimizer.step()

    def predict(self, state: np.ndarray) -> int:
        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            logits, _ = self.model(state_t)
            return int(logits.argmax(dim=1).item())

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "episode_rewards": self._episode_rewards,
        }, str(path))
        logger.info("PPO model saved to %s", path)

    def load(self, path: str | Path) -> None:
        checkpoint = torch.load(str(path), map_location=self.device)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self._episode_rewards = checkpoint.get("episode_rewards", [])
        logger.info("PPO model loaded from %s", path)

    @property
    def episode_rewards(self) -> list[float]:
        return list(self._episode_rewards)
