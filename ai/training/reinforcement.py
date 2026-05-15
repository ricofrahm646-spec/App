"""
Reinforcement Learning for Trading
====================================

Gym-like trading environment with DQN agent, experience replay,
and risk-adjusted reward shaping for learning optimal trade execution.
"""

from __future__ import annotations

import logging
import random
from collections import deque, namedtuple
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

logger = logging.getLogger(__name__)

Transition = namedtuple(
    "Transition", ("state", "action", "reward", "next_state", "done")
)


class Action(IntEnum):
    HOLD = 0
    BUY = 1
    SELL = 2


@dataclass
class EnvironmentConfig:
    """Configuration for the trading environment."""

    initial_balance: float = 10000.0
    commission_rate: float = 0.0002
    slippage_pct: float = 0.0001
    max_position_size: float = 1.0
    risk_free_rate: float = 0.02
    max_drawdown_limit: float = 0.20
    reward_scaling: float = 1.0
    lookback_window: int = 30
    normalize_observations: bool = True


class TradingEnvironment:
    """
    Gym-like trading environment for reinforcement learning.

    State: Market features (OHLCV + indicators) + portfolio state.
    Actions: 0=Hold, 1=Buy, 2=Sell.
    Rewards: Risk-adjusted returns with drawdown penalties.
    """

    def __init__(
        self,
        price_data: np.ndarray,
        feature_data: Optional[np.ndarray] = None,
        config: Optional[EnvironmentConfig] = None,
    ):
        """
        Args:
            price_data: Array of close prices.
            feature_data: Optional pre-computed features (n_bars, n_features).
            config: Environment configuration.
        """
        self.config = config or EnvironmentConfig()
        self.prices = np.asarray(price_data, dtype=np.float64)
        self.n_bars = len(self.prices)

        if feature_data is not None:
            self.features = np.asarray(feature_data, dtype=np.float64)
        else:
            self.features = self._compute_default_features()

        self.observation_size = self.features.shape[1] + 4  # +position, pnl, drawdown, time_frac

        self.current_step = 0
        self.balance = self.config.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.peak_balance = self.config.initial_balance
        self.total_pnl = 0.0
        self.trades: List[Dict[str, Any]] = []
        self._done = False

    @property
    def observation_space_size(self) -> int:
        return self.observation_size

    @property
    def action_space_size(self) -> int:
        return len(Action)

    def reset(self) -> np.ndarray:
        """Reset the environment and return initial observation."""
        self.current_step = self.config.lookback_window
        self.balance = self.config.initial_balance
        self.position = 0.0
        self.entry_price = 0.0
        self.peak_balance = self.config.initial_balance
        self.total_pnl = 0.0
        self.trades = []
        self._done = False
        return self._get_observation()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Execute one step in the environment.

        Args:
            action: 0=Hold, 1=Buy, 2=Sell.

        Returns:
            observation, reward, done, info
        """
        if self._done:
            return self._get_observation(), 0.0, True, {}

        prev_portfolio_value = self._portfolio_value()
        current_price = self.prices[self.current_step]

        trade_info = self._execute_action(Action(action), current_price)

        self.current_step += 1
        if self.current_step >= self.n_bars - 1:
            if self.position != 0:
                self._close_position(self.prices[self.current_step])
            self._done = True

        new_portfolio_value = self._portfolio_value()
        reward = self._compute_reward(prev_portfolio_value, new_portfolio_value, trade_info)

        drawdown = (self.peak_balance - new_portfolio_value) / self.peak_balance
        if drawdown > self.config.max_drawdown_limit:
            if self.position != 0:
                self._close_position(self.prices[self.current_step])
            self._done = True
            reward -= 1.0

        observation = self._get_observation()
        info = {
            "portfolio_value": new_portfolio_value,
            "position": self.position,
            "drawdown": drawdown,
            "n_trades": len(self.trades),
            **trade_info,
        }

        return observation, reward, self._done, info

    def _execute_action(self, action: Action, price: float) -> Dict[str, Any]:
        info: Dict[str, Any] = {"trade_executed": False}

        if action == Action.BUY and self.position <= 0:
            if self.position < 0:
                pnl = self._close_position(price)
                info["close_pnl"] = pnl

            size = self.config.max_position_size
            cost = price * size * (1 + self.config.commission_rate + self.config.slippage_pct)
            if cost <= self.balance:
                self.position = size
                self.entry_price = price * (1 + self.config.slippage_pct)
                self.balance -= price * size * self.config.commission_rate
                info["trade_executed"] = True
                info["action"] = "buy"
                info["price"] = self.entry_price
                info["size"] = size

        elif action == Action.SELL and self.position >= 0:
            if self.position > 0:
                pnl = self._close_position(price)
                info["close_pnl"] = pnl

            size = self.config.max_position_size
            self.position = -size
            self.entry_price = price * (1 - self.config.slippage_pct)
            self.balance -= price * size * self.config.commission_rate
            info["trade_executed"] = True
            info["action"] = "sell"
            info["price"] = self.entry_price
            info["size"] = size

        return info

    def _close_position(self, exit_price: float) -> float:
        if self.position == 0:
            return 0.0

        if self.position > 0:
            adjusted_exit = exit_price * (1 - self.config.slippage_pct)
            pnl = (adjusted_exit - self.entry_price) * self.position
        else:
            adjusted_exit = exit_price * (1 + self.config.slippage_pct)
            pnl = (self.entry_price - adjusted_exit) * abs(self.position)

        commission = exit_price * abs(self.position) * self.config.commission_rate
        pnl -= commission

        self.balance += pnl
        self.total_pnl += pnl
        self.peak_balance = max(self.peak_balance, self.balance)

        self.trades.append({
            "entry_price": self.entry_price,
            "exit_price": exit_price,
            "direction": "long" if self.position > 0 else "short",
            "size": abs(self.position),
            "pnl": pnl,
            "step": self.current_step,
        })

        self.position = 0.0
        self.entry_price = 0.0
        return pnl

    def _portfolio_value(self) -> float:
        current_price = self.prices[min(self.current_step, self.n_bars - 1)]
        unrealized = 0.0
        if self.position > 0:
            unrealized = (current_price - self.entry_price) * self.position
        elif self.position < 0:
            unrealized = (self.entry_price - current_price) * abs(self.position)
        return self.balance + unrealized

    def _get_observation(self) -> np.ndarray:
        idx = min(self.current_step, self.n_bars - 1)
        market_features = self.features[idx].copy()

        position_normalized = self.position / self.config.max_position_size
        pnl_normalized = self.total_pnl / (self.config.initial_balance + 1e-10)
        drawdown = (self.peak_balance - self._portfolio_value()) / (self.peak_balance + 1e-10)
        time_fraction = self.current_step / self.n_bars

        portfolio_features = np.array([
            position_normalized, pnl_normalized, drawdown, time_fraction
        ])

        obs = np.concatenate([market_features, portfolio_features])

        if self.config.normalize_observations:
            obs = np.clip(obs, -10, 10)

        return obs.astype(np.float32)

    def _compute_reward(
        self,
        prev_value: float,
        new_value: float,
        trade_info: Dict[str, Any],
    ) -> float:
        portfolio_return = (new_value - prev_value) / (prev_value + 1e-10)

        reward = portfolio_return * 100.0

        drawdown = (self.peak_balance - new_value) / (self.peak_balance + 1e-10)
        if drawdown > 0.05:
            reward -= drawdown * 2.0

        if trade_info.get("trade_executed"):
            reward -= 0.01

        if self.position == 0:
            reward -= 0.001

        return float(reward * self.config.reward_scaling)

    def _compute_default_features(self) -> np.ndarray:
        n = self.n_bars
        returns = np.zeros(n)
        returns[1:] = np.diff(self.prices) / (self.prices[:-1] + 1e-10)

        vol_5 = np.zeros(n)
        vol_20 = np.zeros(n)
        for i in range(5, n):
            vol_5[i] = np.std(returns[i - 5: i])
        for i in range(20, n):
            vol_20[i] = np.std(returns[i - 20: i])

        sma_10 = np.convolve(self.prices, np.ones(10) / 10, mode="same")
        sma_50 = np.convolve(self.prices, np.ones(50) / 50, mode="same")

        sma_ratio_10 = (self.prices - sma_10) / (sma_10 + 1e-10)
        sma_ratio_50 = (self.prices - sma_50) / (sma_50 + 1e-10)

        rsi = self._compute_rsi(self.prices, 14)

        momentum = np.zeros(n)
        momentum[10:] = self.prices[10:] / (self.prices[:-10] + 1e-10) - 1

        high_20 = np.zeros(n)
        low_20 = np.zeros(n)
        for i in range(20, n):
            high_20[i] = np.max(self.prices[i - 20: i])
            low_20[i] = np.min(self.prices[i - 20: i])
        donchian = (self.prices - low_20) / (high_20 - low_20 + 1e-10)

        features = np.column_stack([
            returns, vol_5, vol_20, sma_ratio_10, sma_ratio_50,
            rsi / 100.0, momentum, donchian,
        ])

        return np.nan_to_num(features, nan=0.0)

    @staticmethod
    def _compute_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        n = len(prices)
        rsi = np.full(n, 50.0)
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        if len(gains) < period:
            return rsi
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                rsi[i + 1] = 100.0
            else:
                rsi[i + 1] = 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)
        return rsi


class ReplayBuffer:
    """Experience replay buffer with prioritized sampling support."""

    def __init__(self, capacity: int = 100000, alpha: float = 0.6):
        self.capacity = capacity
        self.alpha = alpha
        self.buffer: deque = deque(maxlen=capacity)
        self.priorities: deque = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        max_priority = max(self.priorities) if self.priorities else 1.0
        self.buffer.append(Transition(state, action, reward, next_state, done))
        self.priorities.append(max_priority)

    def sample(self, batch_size: int) -> Tuple[List[Transition], np.ndarray, np.ndarray]:
        """Sample a batch with prioritized probabilities."""
        priorities = np.array(self.priorities, dtype=np.float64)
        probs = priorities ** self.alpha
        probs /= probs.sum()

        indices = np.random.choice(len(self.buffer), batch_size, p=probs, replace=False)
        batch = [self.buffer[i] for i in indices]

        weights = (len(self.buffer) * probs[indices]) ** (-0.4)
        weights /= weights.max()

        return batch, indices, weights.astype(np.float32)

    def update_priorities(self, indices: np.ndarray, td_errors: np.ndarray) -> None:
        for idx, td in zip(indices, td_errors):
            self.priorities[idx] = abs(td) + 1e-6

    def __len__(self) -> int:
        return len(self.buffer)


class DuelingDQN(nn.Module):
    """Dueling DQN architecture with separate value and advantage streams."""

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128):
        super().__init__()
        self.feature_layer = nn.Sequential(
            nn.Linear(state_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
        )
        self.value_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, 1),
        )
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Linear(hidden_size // 2, action_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature_layer(x)
        value = self.value_stream(features)
        advantage = self.advantage_stream(features)
        q_values = value + advantage - advantage.mean(dim=-1, keepdim=True)
        return q_values


@dataclass
class DQNConfig:
    """DQN agent configuration."""

    hidden_size: int = 128
    learning_rate: float = 1e-4
    gamma: float = 0.99
    epsilon_start: float = 1.0
    epsilon_end: float = 0.01
    epsilon_decay: int = 10000
    target_update_freq: int = 1000
    batch_size: int = 64
    replay_capacity: int = 100000
    min_replay_size: int = 1000
    double_dqn: bool = True
    device: str = "auto"


class DQNAgent:
    """
    DQN agent for learning trading policies.

    Implements Double DQN with Dueling architecture, prioritized experience
    replay, and epsilon-greedy exploration.
    """

    def __init__(
        self,
        state_size: int,
        action_size: int,
        config: Optional[DQNConfig] = None,
    ):
        self.config = config or DQNConfig()
        self.state_size = state_size
        self.action_size = action_size
        self.device = self._resolve_device()

        self.policy_net = DuelingDQN(state_size, action_size, self.config.hidden_size).to(self.device)
        self.target_net = DuelingDQN(state_size, action_size, self.config.hidden_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(
            self.policy_net.parameters(), lr=self.config.learning_rate
        )
        self.replay_buffer = ReplayBuffer(capacity=self.config.replay_capacity)

        self._step_count = 0
        self._epsilon = self.config.epsilon_start

    def _resolve_device(self) -> torch.device:
        if self.config.device == "auto":
            return torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return torch.device(self.config.device)

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """Select action using epsilon-greedy policy."""
        if training and random.random() < self._epsilon:
            return random.randint(0, self.action_size - 1)

        with torch.no_grad():
            state_tensor = torch.tensor(
                state, dtype=torch.float32
            ).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return int(q_values.argmax(dim=-1).item())

    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        self.replay_buffer.push(state, action, reward, next_state, done)

    def learn(self) -> Optional[float]:
        """Perform one learning step. Returns the loss or None if not enough data."""
        if len(self.replay_buffer) < self.config.min_replay_size:
            return None

        batch_size = min(self.config.batch_size, len(self.replay_buffer))
        transitions, indices, weights = self.replay_buffer.sample(batch_size)

        states = torch.tensor(
            np.array([t.state for t in transitions]), dtype=torch.float32
        ).to(self.device)
        actions = torch.tensor(
            [t.action for t in transitions], dtype=torch.long
        ).to(self.device)
        rewards = torch.tensor(
            [t.reward for t in transitions], dtype=torch.float32
        ).to(self.device)
        next_states = torch.tensor(
            np.array([t.next_state for t in transitions]), dtype=torch.float32
        ).to(self.device)
        dones = torch.tensor(
            [t.done for t in transitions], dtype=torch.float32
        ).to(self.device)
        weight_tensor = torch.tensor(weights, dtype=torch.float32).to(self.device)

        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            if self.config.double_dqn:
                next_actions = self.policy_net(next_states).argmax(dim=-1)
                next_q = self.target_net(next_states).gather(
                    1, next_actions.unsqueeze(1)
                ).squeeze(1)
            else:
                next_q = self.target_net(next_states).max(dim=-1)[0]

            target_q = rewards + self.config.gamma * next_q * (1 - dones)

        td_errors = (current_q - target_q).detach().cpu().numpy()
        self.replay_buffer.update_priorities(indices, td_errors)

        loss = (weight_tensor * F.smooth_l1_loss(current_q, target_q, reduction="none")).mean()

        self.optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()

        self._step_count += 1
        self._update_epsilon()

        if self._step_count % self.config.target_update_freq == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())

        return loss.item()

    def _update_epsilon(self) -> None:
        self._epsilon = self.config.epsilon_end + (
            self.config.epsilon_start - self.config.epsilon_end
        ) * np.exp(-self._step_count / self.config.epsilon_decay)

    def save(self, path: str) -> None:
        torch.save({
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "step_count": self._step_count,
            "epsilon": self._epsilon,
        }, path)

    def load(self, path: str) -> None:
        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.policy_net.load_state_dict(checkpoint["policy_net"])
        self.target_net.load_state_dict(checkpoint["target_net"])
        self.optimizer.load_state_dict(checkpoint["optimizer"])
        self._step_count = checkpoint["step_count"]
        self._epsilon = checkpoint["epsilon"]


@dataclass
class TrainingMetrics:
    """Metrics collected during RL training."""

    episode_rewards: List[float] = field(default_factory=list)
    episode_lengths: List[int] = field(default_factory=list)
    episode_pnls: List[float] = field(default_factory=list)
    episode_trades: List[int] = field(default_factory=list)
    losses: List[float] = field(default_factory=list)
    epsilons: List[float] = field(default_factory=list)


class RLTrainer:
    """
    Episode-based reinforcement learning trainer for the trading agent.
    """

    def __init__(
        self,
        env: TradingEnvironment,
        agent: DQNAgent,
        n_episodes: int = 500,
        max_steps_per_episode: int = 5000,
        eval_interval: int = 50,
        checkpoint_dir: str = "rl_checkpoints",
    ):
        self.env = env
        self.agent = agent
        self.n_episodes = n_episodes
        self.max_steps = max_steps_per_episode
        self.eval_interval = eval_interval
        self.checkpoint_dir = checkpoint_dir
        self.metrics = TrainingMetrics()

        os.makedirs(checkpoint_dir, exist_ok=True)

    def train(self) -> TrainingMetrics:
        """Run the full training loop."""
        best_reward = float("-inf")

        for episode in range(self.n_episodes):
            episode_reward, episode_length, episode_info = self._run_episode(
                training=True
            )

            self.metrics.episode_rewards.append(episode_reward)
            self.metrics.episode_lengths.append(episode_length)
            self.metrics.episode_pnls.append(episode_info.get("total_pnl", 0.0))
            self.metrics.episode_trades.append(episode_info.get("n_trades", 0))
            self.metrics.epsilons.append(self.agent._epsilon)

            if episode % 10 == 0:
                avg_reward = np.mean(self.metrics.episode_rewards[-10:])
                avg_pnl = np.mean(self.metrics.episode_pnls[-10:])
                logger.info(
                    f"Episode {episode}/{self.n_episodes} | "
                    f"Reward: {episode_reward:.2f} | "
                    f"Avg(10): {avg_reward:.2f} | "
                    f"PnL: {episode_info.get('total_pnl', 0):.2f} | "
                    f"Trades: {episode_info.get('n_trades', 0)} | "
                    f"Epsilon: {self.agent._epsilon:.4f}"
                )

            if episode % self.eval_interval == 0 and episode > 0:
                eval_reward, _, eval_info = self._run_episode(training=False)
                logger.info(
                    f"[EVAL] Episode {episode} | "
                    f"Reward: {eval_reward:.2f} | "
                    f"PnL: {eval_info.get('total_pnl', 0):.2f}"
                )

                if eval_reward > best_reward:
                    best_reward = eval_reward
                    self.agent.save(
                        os.path.join(self.checkpoint_dir, "best_agent.pt")
                    )

        self.agent.save(os.path.join(self.checkpoint_dir, "final_agent.pt"))
        return self.metrics

    def _run_episode(
        self, training: bool = True
    ) -> Tuple[float, int, Dict[str, Any]]:
        state = self.env.reset()
        total_reward = 0.0
        step = 0

        for step in range(self.max_steps):
            action = self.agent.select_action(state, training=training)
            next_state, reward, done, info = self.env.step(action)

            if training:
                self.agent.store_transition(state, action, reward, next_state, done)
                loss = self.agent.learn()
                if loss is not None:
                    self.metrics.losses.append(loss)

            total_reward += reward
            state = next_state

            if done:
                break

        episode_info = {
            "total_pnl": self.env.total_pnl,
            "n_trades": len(self.env.trades),
            "final_balance": self.env.balance,
            "max_drawdown": (
                (self.env.peak_balance - self.env.balance)
                / (self.env.peak_balance + 1e-10)
            ),
        }

        return total_reward, step + 1, episode_info

    def evaluate(self, n_episodes: int = 10) -> Dict[str, float]:
        """Evaluate the trained agent over multiple episodes."""
        rewards, pnls, trades, drawdowns = [], [], [], []

        for _ in range(n_episodes):
            reward, length, info = self._run_episode(training=False)
            rewards.append(reward)
            pnls.append(info["total_pnl"])
            trades.append(info["n_trades"])
            drawdowns.append(info["max_drawdown"])

        return {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_pnl": float(np.mean(pnls)),
            "mean_trades": float(np.mean(trades)),
            "mean_max_drawdown": float(np.mean(drawdowns)),
            "win_rate": float(np.mean(np.array(pnls) > 0)),
        }
