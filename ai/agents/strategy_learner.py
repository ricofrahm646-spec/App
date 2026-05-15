"""
JARVIS Strategy Learner - Uses Reinforcement Learning to learn and improve trading strategies
"""
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import random
import json
from loguru import logger


# ---------------------------------------------------------------------------
# Trading Environment
# ---------------------------------------------------------------------------

class TradingEnvironment:
    """Custom gym-like trading environment.

    State vector (per step):
        - Normalised OHLCV for the last `window` bars  (window * 5 features)
        - RSI(14), MACD, Signal, BB_upper, BB_lower, BB_mid
        - ATR(14)
        - account equity ratio, position flag (-1/0/1), unrealised PnL ratio
    Total state dim = window * 5 + 10

    Actions:
        0 = HOLD
        1 = BUY  (open long)
        2 = SELL (open short)
        3 = CLOSE (close any open position)
    """

    HOLD  = 0
    BUY   = 1
    SELL  = 2
    CLOSE = 3

    def __init__(self, data: np.ndarray, initial_balance: float = 10_000.0,
                 window: int = 20, commission: float = 0.0001,
                 sl_pct: float = 0.01, tp_pct: float = 0.02):
        """
        Args:
            data:            numpy array shape (N, 5) – OHLCV columns.
            initial_balance: starting account balance.
            window:          look-back window for state features.
            commission:      commission per trade as a fraction of price.
            sl_pct:          stop-loss as fraction of entry price.
            tp_pct:          take-profit as fraction of entry price.
        """
        assert data.ndim == 2 and data.shape[1] >= 5, "data must be shape (N,5) OHLCV"
        self.raw_data        = data.astype(np.float64)
        self.initial_balance = initial_balance
        self.window          = window
        self.commission      = commission
        self.sl_pct          = sl_pct
        self.tp_pct          = tp_pct

        self.n_features = window * 5 + 10  # state dimension
        self.n_actions  = 4

        self._precompute_indicators()
        self.reset()

    # ------------------------------------------------------------------
    def _precompute_indicators(self) -> None:
        """Pre-compute technical indicators for all bars."""
        closes = self.raw_data[:, 3]
        highs  = self.raw_data[:, 1]
        lows   = self.raw_data[:, 2]
        N = len(closes)

        # RSI(14)
        self.rsi = self._calc_rsi(closes, 14)

        # MACD (12, 26, 9)
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd_line  = ema12 - ema26
        signal_line = self._ema(macd_line, 9)
        self.macd   = macd_line
        self.macd_signal = signal_line

        # Bollinger Bands (20, 2)
        self.bb_mid   = np.zeros(N)
        self.bb_upper = np.zeros(N)
        self.bb_lower = np.zeros(N)
        for i in range(19, N):
            w = closes[i-19:i+1]
            mu = w.mean()
            sd = w.std(ddof=0)
            self.bb_mid[i]   = mu
            self.bb_upper[i] = mu + 2 * sd
            self.bb_lower[i] = mu - 2 * sd

        # ATR(14)
        self.atr = self._calc_atr(highs, lows, closes, 14)

    # ------------------------------------------------------------------
    @staticmethod
    def _ema(arr: np.ndarray, period: int) -> np.ndarray:
        result = np.zeros_like(arr)
        k = 2.0 / (period + 1)
        result[0] = arr[0]
        for i in range(1, len(arr)):
            result[i] = arr[i] * k + result[i-1] * (1 - k)
        return result

    @staticmethod
    def _calc_rsi(closes: np.ndarray, period: int) -> np.ndarray:
        rsi = np.zeros(len(closes))
        deltas = np.diff(closes)
        gains  = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        for i in range(period, len(closes)):
            j = i - period
            avg_gain = (avg_gain * (period - 1) + gains[j]) / period
            avg_loss = (avg_loss * (period - 1) + losses[j]) / period
            rs = avg_gain / (avg_loss + 1e-10)
            rsi[i] = 100 - 100 / (1 + rs)
        return rsi

    @staticmethod
    def _calc_atr(highs: np.ndarray, lows: np.ndarray,
                  closes: np.ndarray, period: int) -> np.ndarray:
        N = len(closes)
        tr = np.zeros(N)
        for i in range(1, N):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i]  - closes[i-1])
            tr[i] = max(hl, hc, lc)
        atr = np.zeros(N)
        atr[period] = tr[1:period+1].mean()
        for i in range(period+1, N):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
        return atr

    # ------------------------------------------------------------------
    def _build_state(self) -> np.ndarray:
        idx = self.current_step
        # OHLCV window – normalise by the close of the first bar in the window
        ohlcv_window = self.raw_data[idx - self.window + 1: idx + 1].copy()
        norm_factor  = ohlcv_window[0, 3] if ohlcv_window[0, 3] != 0 else 1.0
        ohlcv_norm   = ohlcv_window / norm_factor
        ohlcv_flat   = ohlcv_norm.flatten()

        close = self.raw_data[idx, 3]
        indicators = np.array([
            self.rsi[idx]          / 100.0,
            self.macd[idx]         / (close + 1e-10),
            self.macd_signal[idx]  / (close + 1e-10),
            self.bb_upper[idx]     / (close + 1e-10),
            self.bb_lower[idx]     / (close + 1e-10),
            self.bb_mid[idx]       / (close + 1e-10),
            self.atr[idx]          / (close + 1e-10),
            self.equity / self.initial_balance,
            float(self.position),          # -1, 0, or +1
            self.unrealised_pnl / (self.initial_balance + 1e-10),
        ], dtype=np.float64)

        state = np.concatenate([ohlcv_flat, indicators])
        return np.nan_to_num(state, nan=0.0, posinf=1.0, neginf=-1.0).astype(np.float32)

    # ------------------------------------------------------------------
    def reset(self) -> np.ndarray:
        self.current_step    = self.window - 1
        self.balance         = self.initial_balance
        self.equity          = self.initial_balance
        self.position        = 0        # -1=short, 0=flat, 1=long
        self.entry_price     = 0.0
        self.entry_step      = 0
        self.unrealised_pnl  = 0.0
        self.total_trades    = 0
        self.winning_trades  = 0
        self.trade_history: List[Dict] = []
        self.equity_curve: List[float] = [self.initial_balance]
        return self._build_state()

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action, advance one bar, return (next_state, reward, done, info)."""
        current_price = self.raw_data[self.current_step, 3]  # close
        reward = 0.0
        info: Dict = {}

        # --- Execute action ---
        if action == self.BUY and self.position == 0:
            self.position    = 1
            self.entry_price = current_price * (1 + self.commission)
            self.entry_step  = self.current_step
            self.total_trades += 1

        elif action == self.SELL and self.position == 0:
            self.position    = -1
            self.entry_price = current_price * (1 - self.commission)
            self.entry_step  = self.current_step
            self.total_trades += 1

        elif action == self.CLOSE and self.position != 0:
            exit_price = current_price * (1 - self.commission * self.position)
            pnl = (exit_price - self.entry_price) * self.position
            self.balance        += pnl
            self.equity          = self.balance
            self.unrealised_pnl  = 0.0
            if pnl > 0:
                self.winning_trades += 1
            trade = {
                "entry_step":  self.entry_step,
                "exit_step":   self.current_step,
                "entry_price": self.entry_price,
                "exit_price":  exit_price,
                "direction":   self.position,
                "pnl":         pnl,
            }
            self.trade_history.append(trade)
            reward = self._calculate_reward(pnl, self._max_drawdown())
            self.position    = 0
            self.entry_price = 0.0
            info["trade"] = trade

        # Auto SL/TP check when in position
        if self.position != 0:
            close = self.raw_data[self.current_step, 3]
            self.unrealised_pnl = (close - self.entry_price) * self.position
            # Check stop-loss
            if self.unrealised_pnl / (self.entry_price + 1e-10) <= -self.sl_pct:
                pnl = self.unrealised_pnl - self.entry_price * self.commission
                self.balance        += pnl
                self.equity          = self.balance
                self.unrealised_pnl  = 0.0
                self.trade_history.append({
                    "entry_step": self.entry_step, "exit_step": self.current_step,
                    "entry_price": self.entry_price, "exit_price": close,
                    "direction": self.position, "pnl": pnl, "exit_reason": "SL"
                })
                reward = self._calculate_reward(pnl, self._max_drawdown())
                self.position = 0
            # Check take-profit
            elif self.unrealised_pnl / (self.entry_price + 1e-10) >= self.tp_pct:
                pnl = self.unrealised_pnl - self.entry_price * self.commission
                self.balance        += pnl
                self.equity          = self.balance
                self.unrealised_pnl  = 0.0
                self.winning_trades += 1
                self.trade_history.append({
                    "entry_step": self.entry_step, "exit_step": self.current_step,
                    "entry_price": self.entry_price, "exit_price": close,
                    "direction": self.position, "pnl": pnl, "exit_reason": "TP"
                })
                reward = self._calculate_reward(pnl, self._max_drawdown())
                self.position = 0

        self.equity = self.balance + self.unrealised_pnl
        self.equity_curve.append(self.equity)

        self.current_step += 1
        done = self.current_step >= len(self.raw_data) - 1

        if done and self.position != 0:
            close = self.raw_data[self.current_step - 1, 3]
            pnl   = (close - self.entry_price) * self.position
            self.balance += pnl
            self.equity   = self.balance
            self.position = 0

        next_state = self._build_state() if not done else np.zeros(self.n_features, dtype=np.float32)
        info.update({
            "balance":     self.balance,
            "equity":      self.equity,
            "total_trades": self.total_trades,
        })
        return next_state, float(reward), done, info

    def _calculate_reward(self, profit: float, drawdown: float) -> float:
        """Risk-adjusted reward: Sharpe-like metric."""
        base     = profit / (self.initial_balance + 1e-10)
        dd_penalty = drawdown * 2.0          # penalise drawdown heavily
        trade_bonus = 0.001 if profit > 0 else -0.001
        return float(base - dd_penalty + trade_bonus)

    def _max_drawdown(self) -> float:
        if len(self.equity_curve) < 2:
            return 0.0
        curve = np.array(self.equity_curve)
        peak  = np.maximum.accumulate(curve)
        dd    = (peak - curve) / (peak + 1e-10)
        return float(dd.max())

    @property
    def state_dim(self) -> int:
        return self.n_features


# ---------------------------------------------------------------------------
# Neural Network
# ---------------------------------------------------------------------------

class TradingDQN(nn.Module):
    """Deep Q-Network for trading decisions."""

    def __init__(self, state_dim: int, action_dim: int = 4, hidden_dim: int = 256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, action_dim),
        )
        self._init_weights()

    def _init_weights(self):
        for layer in self.net:
            if isinstance(layer, nn.Linear):
                nn.init.orthogonal_(layer.weight, gain=np.sqrt(2))
                nn.init.zeros_(layer.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


# ---------------------------------------------------------------------------
# Replay Buffer
# ---------------------------------------------------------------------------

class ReplayBuffer:
    """Experience replay buffer with uniform sampling."""

    def __init__(self, capacity: int = 50_000):
        self.buffer: deque = deque(maxlen=capacity)

    def push(self, state: np.ndarray, action: int, reward: float,
             next_state: np.ndarray, done: bool) -> None:
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> Tuple:
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            np.array(states,      dtype=np.float32),
            np.array(actions,     dtype=np.int64),
            np.array(rewards,     dtype=np.float32),
            np.array(next_states, dtype=np.float32),
            np.array(dones,       dtype=np.float32),
        )

    def __len__(self) -> int:
        return len(self.buffer)


# ---------------------------------------------------------------------------
# Strategy Learner (DQN agent)
# ---------------------------------------------------------------------------

class StrategyLearner:
    """DQN-based strategy learner with experience replay and target network."""

    def __init__(
        self,
        state_dim:    int   = 110,   # window(20)*5 + 10
        action_dim:   int   = 4,
        hidden_dim:   int   = 256,
        lr:           float = 3e-4,
        gamma:        float = 0.99,
        epsilon_start:float = 1.0,
        epsilon_end:  float = 0.05,
        epsilon_decay:int   = 10_000,
        batch_size:   int   = 64,
        replay_size:  int   = 50_000,
        target_update:int   = 200,   # steps between target network updates
    ):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"StrategyLearner using device: {self.device}")

        self.gamma         = gamma
        self.epsilon       = epsilon_start
        self.epsilon_end   = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size    = batch_size
        self.target_update = target_update
        self.steps_done    = 0

        self.policy_net = TradingDQN(state_dim, action_dim, hidden_dim).to(self.device)
        self.target_net = TradingDQN(state_dim, action_dim, hidden_dim).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=lr)
        self.replay    = ReplayBuffer(replay_size)
        self.loss_fn   = nn.SmoothL1Loss()

        self.training_history: List[Dict] = []

    # ------------------------------------------------------------------
    def _epsilon(self) -> float:
        """Exponential epsilon decay."""
        return self.epsilon_end + (self.epsilon - self.epsilon_end) * \
               np.exp(-self.steps_done / self.epsilon_decay)

    def predict(self, state: np.ndarray) -> int:
        """Greedy action selection (no exploration)."""
        self.policy_net.eval()
        with torch.no_grad():
            t = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(t)
        return int(q_values.argmax(dim=1).item())

    def _select_action(self, state: np.ndarray) -> int:
        """Epsilon-greedy action selection during training."""
        eps = self._epsilon()
        self.steps_done += 1
        if random.random() < eps:
            return random.randrange(4)
        return self.predict(state)

    def _optimize(self) -> Optional[float]:
        """One gradient update step."""
        if len(self.replay) < self.batch_size:
            return None

        states, actions, rewards, next_states, dones = self.replay.sample(self.batch_size)

        s  = torch.FloatTensor(states).to(self.device)
        a  = torch.LongTensor(actions).unsqueeze(1).to(self.device)
        r  = torch.FloatTensor(rewards).to(self.device)
        ns = torch.FloatTensor(next_states).to(self.device)
        d  = torch.FloatTensor(dones).to(self.device)

        self.policy_net.train()
        current_q = self.policy_net(s).gather(1, a).squeeze(1)

        with torch.no_grad():
            # Double DQN: action selected by policy net, evaluated by target net
            next_actions = self.policy_net(ns).argmax(dim=1, keepdim=True)
            next_q       = self.target_net(ns).gather(1, next_actions).squeeze(1)
            target_q     = r + self.gamma * next_q * (1 - d)

        loss = self.loss_fn(current_q, target_q)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        return float(loss.item())

    # ------------------------------------------------------------------
    def train(self, env: TradingEnvironment, episodes: int = 1000) -> Dict:
        """Train the DQN agent on the given environment.

        Returns:
            dict with keys: episode_rewards, episode_profits,
                             win_rates, avg_loss, best_episode
        """
        episode_rewards: List[float] = []
        episode_profits: List[float] = []
        win_rates:        List[float] = []
        losses:           List[float] = []
        best_profit       = -np.inf
        best_episode      = 0

        for ep in range(1, episodes + 1):
            state     = env.reset()
            ep_reward = 0.0
            ep_loss   = 0.0
            loss_count = 0

            while True:
                action = self._select_action(state)
                next_state, reward, done, info = env.step(action)
                self.replay.push(state, action, reward, next_state, done)

                ep_reward += reward
                state      = next_state

                loss = self._optimize()
                if loss is not None:
                    ep_loss    += loss
                    loss_count += 1

                if self.steps_done % self.target_update == 0:
                    self.target_net.load_state_dict(self.policy_net.state_dict())

                if done:
                    break

            profit   = env.balance - env.initial_balance
            win_rate = env.winning_trades / max(env.total_trades, 1)
            avg_loss = ep_loss / max(loss_count, 1)

            episode_rewards.append(ep_reward)
            episode_profits.append(profit)
            win_rates.append(win_rate)
            losses.append(avg_loss)

            if profit > best_profit:
                best_profit  = profit
                best_episode = ep

            if ep % 50 == 0 or ep == 1:
                logger.info(
                    f"Episode {ep}/{episodes} | "
                    f"Profit: {profit:.2f} | WinRate: {win_rate:.2%} | "
                    f"ε: {self._epsilon():.3f} | Loss: {avg_loss:.5f}"
                )

        result = {
            "episode_rewards": episode_rewards,
            "episode_profits": episode_profits,
            "win_rates":        win_rates,
            "avg_losses":       losses,
            "best_episode":     best_episode,
            "best_profit":      best_profit,
            "final_epsilon":    self._epsilon(),
            "total_steps":      self.steps_done,
        }
        self.training_history.append(result)
        return result

    # ------------------------------------------------------------------
    def save_model(self, path: str) -> bool:
        """Save policy network weights and training metadata."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            checkpoint = {
                "policy_state_dict": self.policy_net.state_dict(),
                "target_state_dict": self.target_net.state_dict(),
                "optimizer_state":   self.optimizer.state_dict(),
                "steps_done":        self.steps_done,
                "epsilon":           self._epsilon(),
            }
            torch.save(checkpoint, str(p))
            logger.info(f"Model saved: {p}")
            return True
        except Exception as exc:
            logger.error(f"Failed to save model: {exc}")
            return False

    def load_model(self, path: str) -> bool:
        """Load policy network weights from checkpoint."""
        try:
            checkpoint = torch.load(path, map_location=self.device, weights_only=False)
            self.policy_net.load_state_dict(checkpoint["policy_state_dict"])
            self.target_net.load_state_dict(checkpoint["target_state_dict"])
            self.optimizer.load_state_dict(checkpoint["optimizer_state"])
            self.steps_done = checkpoint.get("steps_done", 0)
            logger.info(f"Model loaded: {path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to load model: {exc}")
            return False

    def evaluate(self, env: TradingEnvironment) -> Dict:
        """Run a greedy evaluation episode and return performance metrics."""
        state = env.reset()
        self.policy_net.eval()
        while True:
            action = self.predict(state)
            state, _, done, _ = env.step(action)
            if done:
                break

        final_equity = env.equity
        total_return = (final_equity - env.initial_balance) / env.initial_balance
        win_rate     = env.winning_trades / max(env.total_trades, 1)

        # Sharpe approximation from equity curve
        eq_arr   = np.array(env.equity_curve)
        returns  = np.diff(eq_arr) / (eq_arr[:-1] + 1e-10)
        sharpe   = float(returns.mean() / (returns.std() + 1e-10) * np.sqrt(252))

        return {
            "final_equity":  final_equity,
            "total_return":  total_return,
            "total_trades":  env.total_trades,
            "win_rate":      win_rate,
            "sharpe":        sharpe,
            "max_drawdown":  env._max_drawdown(),
        }
