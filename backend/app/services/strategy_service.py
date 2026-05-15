"""
Strategy Service - CRUD and performance management for trading strategies.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.strategy import Strategy, StrategyStatus, StrategyType

logger = logging.getLogger(__name__)


class StrategyService:

    @staticmethod
    def list_strategies(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[StrategyStatus] = None,
    ) -> List[Strategy]:
        q = db.query(Strategy)
        if status:
            q = q.filter(Strategy.status == status)
        return q.offset(skip).limit(limit).all()

    @staticmethod
    def get_strategy(db: Session, strategy_id: int) -> Optional[Strategy]:
        return db.query(Strategy).filter(Strategy.id == strategy_id).first()

    @staticmethod
    def create_strategy(db: Session, data: Dict[str, Any]) -> Strategy:
        strategy = Strategy(
            name=data["name"],
            type=data.get("type", StrategyType.CUSTOM),
            description=data.get("description", ""),
            config=data.get("config", {}),
            is_ai_generated=data.get("is_ai_generated", False),
            ai_model_used=data.get("ai_model_used"),
            source_code=data.get("source_code"),
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        logger.info("Created strategy #%d: %s", strategy.id, strategy.name)
        return strategy

    @staticmethod
    def update_strategy(db: Session, strategy_id: int, data: Dict[str, Any]) -> Optional[Strategy]:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None
        allowed = {"name", "description", "config", "type", "source_code"}
        for key, val in data.items():
            if key in allowed:
                setattr(strategy, key, val)
        strategy.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(strategy)
        return strategy

    @staticmethod
    def delete_strategy(db: Session, strategy_id: int) -> bool:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return False
        db.delete(strategy)
        db.commit()
        return True

    @staticmethod
    def activate_strategy(db: Session, strategy_id: int) -> Optional[Strategy]:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None
        strategy.status = StrategyStatus.ACTIVE
        strategy.activated_at = datetime.utcnow()
        strategy.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(strategy)
        logger.info("Activated strategy #%d: %s", strategy.id, strategy.name)
        return strategy

    @staticmethod
    def deactivate_strategy(db: Session, strategy_id: int) -> Optional[Strategy]:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None
        strategy.status = StrategyStatus.INACTIVE
        strategy.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(strategy)
        return strategy

    @staticmethod
    def get_active_strategies(db: Session) -> List[Strategy]:
        return db.query(Strategy).filter(Strategy.status == StrategyStatus.ACTIVE).all()

    @staticmethod
    def update_performance(db: Session, strategy_id: int, metrics: Dict[str, float]) -> Optional[Strategy]:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return None
        for field in [
            "total_trades", "winning_trades", "losing_trades",
            "total_profit", "total_loss", "win_rate", "profit_factor",
            "max_drawdown", "sharpe_ratio", "avg_trade_duration",
        ]:
            if field in metrics:
                setattr(strategy, field, metrics[field])
        strategy.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(strategy)
        return strategy

    @staticmethod
    def get_performance_metrics(db: Session, strategy_id: int) -> Dict[str, Any]:
        strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            return {}
        net_profit = strategy.total_profit - abs(strategy.total_loss)
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "status": strategy.status,
            "total_trades": strategy.total_trades,
            "winning_trades": strategy.winning_trades,
            "losing_trades": strategy.losing_trades,
            "win_rate": strategy.win_rate,
            "profit_factor": strategy.profit_factor,
            "net_profit": round(net_profit, 2),
            "total_profit": strategy.total_profit,
            "total_loss": strategy.total_loss,
            "max_drawdown": strategy.max_drawdown,
            "sharpe_ratio": strategy.sharpe_ratio,
            "avg_trade_duration": strategy.avg_trade_duration,
            "last_trade_at": strategy.last_trade_at.isoformat() if strategy.last_trade_at else None,
            "activated_at": strategy.activated_at.isoformat() if strategy.activated_at else None,
        }

    @staticmethod
    def evaluate_and_rank(db: Session) -> List[Dict[str, Any]]:
        """Score and rank all strategies by composite performance."""
        strategies = db.query(Strategy).all()
        ranked = []
        for s in strategies:
            score = 0.0
            if s.win_rate:
                score += s.win_rate * 30
            if s.profit_factor:
                score += min(s.profit_factor, 3.0) * 20
            if s.sharpe_ratio:
                score += min(s.sharpe_ratio, 3.0) * 20
            if s.max_drawdown:
                score -= s.max_drawdown * 5
            if s.total_trades:
                score += min(s.total_trades, 100) * 0.1
            ranked.append({
                "id": s.id,
                "name": s.name,
                "type": s.type,
                "status": s.status,
                "score": round(score, 2),
                "win_rate": s.win_rate,
                "profit_factor": s.profit_factor,
                "sharpe_ratio": s.sharpe_ratio,
                "max_drawdown": s.max_drawdown,
                "total_trades": s.total_trades,
            })
        return sorted(ranked, key=lambda x: x["score"], reverse=True)
