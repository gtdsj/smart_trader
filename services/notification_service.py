# -*- coding: utf-8 -*-
"""
通知提醒服务模块
"""

import traceback
import asyncio
import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

import aiohttp
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from core.time_utils import TimeUtils

from config import get_settings
from core.database import get_db, NotificationLog
from core.cache_adapter import get_cache_client


class NotificationType(Enum):
    """通知类型枚举"""
    TRADE_SIGNAL = "trade_signal"  # 交易信号
    ORDER_FILLED = "order_filled"  # 订单成交
    POSITION_ALERT = "position_alert"  # 持仓预警
    SYSTEM_ERROR = "system_error"  # 系统错误
    STRATEGY_ALERT = "strategy_alert"  # 策略预警
    MARKET_ALERT = "market_alert"  # 市场预警


class NotificationLevel(Enum):
    """通知级别枚举"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DingTalkBot:
    """钉钉机器人"""
    
    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成签名"""
        if not self.secret:
            return ""
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return sign
    
    async def send_text(self, content: str, at_mobiles: Optional[List[str]] = None, 
                       at_all: bool = False) -> bool:
        """发送文本消息"""
        # 使用TimeUtils获取当前毫秒时间戳
        current_time = TimeUtils.normalize_timestamp(datetime.now())
        timestamp = str(int(current_time.timestamp() * 1000))
        sign = self._generate_sign(timestamp)
        
        url = self.webhook_url
        if sign:
            url += f"&timestamp={timestamp}&sign={sign}"
        
        data = {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }
        
        if at_mobiles or at_all:
            data["at"] = {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        logger.info("钉钉消息发送成功")
                        return True
                    else:
                        logger.error(f"钉钉消息发送失败: {result}")
                        return False
        except Exception as e:
            logger.error(f"钉钉消息发送异常: {e}, {traceback.format_exc()}")
            return False
    
    async def send_markdown(self, title: str, text: str, 
                           at_mobiles: Optional[List[str]] = None, 
                           at_all: bool = False) -> bool:
        """发送Markdown消息"""
        # 使用TimeUtils获取当前毫秒时间戳
        current_time = TimeUtils.normalize_timestamp(datetime.now())
        timestamp = str(int(current_time.timestamp() * 1000))
        sign = self._generate_sign(timestamp)
        
        url = self.webhook_url
        if sign:
            url += f"&timestamp={timestamp}&sign={sign}"
        
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            }
        }
        
        if at_mobiles or at_all:
            data["at"] = {
                "atMobiles": at_mobiles or [],
                "isAtAll": at_all
            }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    result = await response.json()
                    if result.get("errcode") == 0:
                        logger.info("钉钉Markdown消息发送成功")
                        return True
                    else:
                        logger.error(f"钉钉Markdown消息发送失败: {result}")
                        return False
        except Exception as e:
            logger.error(f"钉钉Markdown消息发送异常: {e}, {traceback.format_exc()}")
            return False


class NotificationService:
    """通知服务"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_client = get_cache_client()
        self.dingtalk_bot = None
        
        # 初始化钉钉机器人
        if self.settings.dingtalk.enabled and self.settings.dingtalk.webhook_url:
            self.dingtalk_bot = DingTalkBot(
                webhook_url=self.settings.dingtalk.webhook_url,
                secret=self.settings.dingtalk.secret
            )
    
    async def _save_notification_log(self, notification_type: str, title: str,
                                   content: str, recipient: str, status: str, 
                                   error_message: Optional[str] = None):
        """保存通知日志"""
        try:
            # 确保数据库已初始化
            from core.database import init_database, SessionLocal
            if SessionLocal is None:
                init_database()
            
            for db in get_db():
                log_data = {
                    "notification_type": notification_type,
                    "title": title,
                    "content": content,
                    "recipient": recipient,
                    "status": status,
                    "error_message": error_message,
                    "created_at": datetime.now()
                }
                
                stmt = insert(NotificationLog).values(**log_data)
                db.execute(stmt)
                db.commit()
                break
        except Exception as e:
            logger.error(f"保存通知日志失败: {e}")
    
    async def send_dingtalk_notification(self, title: str, content: str, 
                                       notification_type: NotificationType = NotificationType.TRADE_SIGNAL,
                                       level: NotificationLevel = NotificationLevel.INFO,
                                       at_mobiles: Optional[List[str]] = None,
                                       at_all: bool = False) -> bool:
        """发送钉钉通知"""
        if not self.dingtalk_bot:
            logger.warning("钉钉机器人未配置")
            return False
        
        # 根据级别添加emoji和颜色
        level_emoji = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨"
        }
        
        level_color = {
            NotificationLevel.INFO: "#1890ff",
            NotificationLevel.WARNING: "#faad14",
            NotificationLevel.ERROR: "#f5222d",
            NotificationLevel.CRITICAL: "#722ed1"
        }
        
        emoji = level_emoji.get(level, "ℹ️")
        
        # 构建Markdown消息
        markdown_text = f"""
# {emoji} {title}

**通知类型**: {notification_type.value}
**通知级别**: {level.value}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{content}

---

> 来自智能量化交易系统
        """.strip()
        
        try:
            success = await self.dingtalk_bot.send_markdown(
                title=f"{emoji} {title}",
                text=markdown_text,
                at_mobiles=at_mobiles,
                at_all=at_all
            )
            
            # 保存通知日志
            await self._save_notification_log(
                notification_type=notification_type.value,
                title=title,
                content=content,
                recipient="dingtalk",
                status="success" if success else "failed",
                error_message=None if success else "发送失败"
            )
            
            return success
        except Exception as e:
            logger.error(f"发送钉钉通知失败: {e}, {traceback.format_exc()}")
            await self._save_notification_log(
                notification_type=notification_type.value,
                title=title,
                content=content,
                recipient="dingtalk",
                status="error",
                error_message=str(e)
            )
            return False
    
    async def send_trade_signal_notification(self, stock_code: str, signal_type: str, 
                                           price: float, reason: str, 
                                           strategy_name: str) -> bool:
        """发送交易信号通知"""
        title = f"交易信号 - {stock_code}"
        content = f"""
**股票代码**: {stock_code}
**信号类型**: {signal_type}
**价格**: {price:.2f}
**策略**: {strategy_name}
**原因**: {reason}
        """.strip()
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content,
            notification_type=NotificationType.TRADE_SIGNAL,
            level=NotificationLevel.INFO
        )
    
    async def send_order_filled_notification(self, order_id: str, stock_code: str, 
                                           order_type: str, volume: int, 
                                           price: float) -> bool:
        """发送订单成交通知"""
        title = f"订单成交 - {stock_code}"
        content = f"""
**订单ID**: {order_id}
**股票代码**: {stock_code}
**交易类型**: {order_type}
**成交数量**: {volume}
**成交价格**: {price:.2f}
**成交金额**: {volume * price:.2f}
        """.strip()
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content,
            notification_type=NotificationType.ORDER_FILLED,
            level=NotificationLevel.INFO
        )
    
    async def send_position_alert_notification(self, stock_code: str, alert_type: str, 
                                             current_price: float, target_price: float, 
                                             profit_loss_ratio: float) -> bool:
        """发送持仓预警通知"""
        title = f"持仓预警 - {stock_code}"
        content = f"""
**股票代码**: {stock_code}
**预警类型**: {alert_type}
**当前价格**: {current_price:.2f}
**目标价格**: {target_price:.2f}
**盈亏比例**: {profit_loss_ratio:.2%}
        """.strip()
        
        level = NotificationLevel.WARNING if abs(profit_loss_ratio) > 0.05 else NotificationLevel.INFO
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content,
            notification_type=NotificationType.POSITION_ALERT,
            level=level
        )
    
    async def send_system_error_notification(self, error_type: str, error_message: str, 
                                           module: str) -> bool:
        """发送系统错误通知"""
        title = f"系统错误 - {module}"
        content = f"""
**错误类型**: {error_type}
**模块**: {module}
**错误信息**: {error_message}
**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content,
            notification_type=NotificationType.SYSTEM_ERROR,
            level=NotificationLevel.ERROR,
            at_all=True  # 系统错误@所有人
        )
    
    async def send_strategy_alert_notification(self, strategy_name: str, alert_message: str, 
                                             performance_data: Optional[Dict[str, Any]] = None) -> bool:
        """发送策略预警通知"""
        title = f"策略预警 - {strategy_name}"
        content = f"""
**策略名称**: {strategy_name}
**预警信息**: {alert_message}
        """
        
        if performance_data:
            content += "\n\n**性能数据**:\n"
            for key, value in performance_data.items():
                if isinstance(value, float):
                    content += f"- {key}: {value:.4f}\n"
                else:
                    content += f"- {key}: {value}\n"
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content.strip(),
            notification_type=NotificationType.STRATEGY_ALERT,
            level=NotificationLevel.WARNING
        )
    
    async def send_market_alert_notification(self, market_condition: str, 
                                           description: str, 
                                           impact_level: str) -> bool:
        """发送市场预警通知"""
        title = f"市场预警 - {market_condition}"
        content = f"""
**市场状况**: {market_condition}
**影响级别**: {impact_level}
**描述**: {description}
        """.strip()
        
        level_mapping = {
            "低": NotificationLevel.INFO,
            "中": NotificationLevel.WARNING,
            "高": NotificationLevel.ERROR,
            "极高": NotificationLevel.CRITICAL
        }
        
        level = level_mapping.get(impact_level, NotificationLevel.INFO)
        
        return await self.send_dingtalk_notification(
            title=title,
            content=content,
            notification_type=NotificationType.MARKET_ALERT,
            level=level
        )
    
    async def get_notification_history(self, limit: int = 100, 
                                     notification_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取通知历史"""
        try:
            async for db in get_db():
                query = select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
                
                if notification_type:
                    query = query.where(NotificationLog.notification_type == notification_type)
                
                result = await db.execute(query)
                logs = result.scalars().all()
                
                return [
                    {
                        "id": log.id,
                        "notification_type": log.notification_type,
                        "title": log.title,
                        "content": log.content,
                        "recipient": log.recipient,
                        "status": log.status,
                        "error_message": log.error_message,
                        "created_at": log.created_at.isoformat() if log.created_at else None
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"获取通知历史失败: {e}, {traceback.format_exc()}")
            return []