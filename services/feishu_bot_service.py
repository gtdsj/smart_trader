# -*- coding: utf-8 -*-
"""
飞书机器人服务
提供飞书机器人消息处理和响应功能
"""

import json
import re
import traceback
import threading
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import lark_oapi as lark
from lark_oapi.api.im.v1 import *

from config import get_settings
from utils.log_config import get_logger
from services.stock_screener import StockScreener
from services.data_service import DataService
from services.strategy_manager import StrategyManager

# 获取logger实例
logger = get_logger(__name__)


class FeishuBotService:
    """飞书机器人服务类"""
    
    def __init__(self, app_id: str, app_secret: str, loop=None):
        """初始化飞书机器人服务
        
        Args:
            app_id: 飞书应用ID
            app_secret: 飞书应用密钥
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = None
        self.ws_client = None
        self.event_handler = None
        self.stock_screener = None
        self.data_service = None
        self._running = False
        self._stop_event = threading.Event()
        self._ws_thread = None
        self.loop = loop or asyncio.get_event_loop()
        
        # 初始化服务依赖
        self._init_services()
        
        # 初始化飞书客户端和事件处理器
        self._init_feishu_client()
        self._init_event_handler()
        
        logger.info("飞书机器人服务初始化完成")
    
    def set_stock_screener(self, stock_screener):
        """设置股票筛选服务"""
        self.stock_screener = stock_screener
    
    def set_data_service(self, data_service):
        """设置数据服务"""
        self.data_service = data_service
    
    def _init_services(self):
        """初始化服务依赖"""
        try:
            self.data_service = DataService.get_instance()
            self.strategy_manager = StrategyManager()
            self.strategy_manager.set_data_service(self.data_service)
            self.stock_screener = StockScreener(self.data_service)
            logger.info("飞书机器人服务依赖初始化完成")
        except Exception as e:
            logger.error(f"初始化服务依赖失败: {e}, {traceback.format_exc()}")
            raise
    
    def _init_feishu_client(self):
        """初始化飞书客户端"""
        try:
            # 创建飞书客户端
            self.client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .build()
            
            logger.info("飞书客户端初始化完成")
        except Exception as e:
            logger.error(f"初始化飞书客户端失败: {e}, {traceback.format_exc()}")
            raise
    
    def _init_event_handler(self):
        """初始化事件处理器"""
        try:
            # 创建事件处理器
            self.event_handler = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(self._handle_message)
                .build()
            )
            
            # 创建WebSocket客户端
            self.ws_client = lark.ws.Client(
                self.app_id,
                self.app_secret,
                event_handler=self.event_handler,
                log_level=lark.LogLevel.INFO
            )
            
            logger.info("飞书事件处理器初始化成功")
            
        except Exception as e:
            logger.error(f"初始化飞书事件处理器失败: {e}, {traceback.format_exc()}")
            raise
    
    def start(self) -> None:
        """启动飞书机器人"""
        try:
            logger.info("正在启动飞书机器人...")
            self._running = True
            self._stop_event.clear()
            
            # 在单独的线程中启动WebSocket客户端
            def _start_ws_client():
                try:
                    logger.info("飞书机器人WebSocket客户端启动中...")
                    self.ws_client.start()
                except KeyboardInterrupt:
                    logger.info("飞书机器人WebSocket客户端接收到中断信号")
                except Exception as e:
                    if self._running:
                        logger.error(f"飞书机器人WebSocket客户端异常: {e}")
                    else:
                        logger.info("飞书机器人WebSocket客户端正常停止")
                finally:
                    logger.info("飞书机器人WebSocket客户端已退出")
            
            self._ws_thread = threading.Thread(target=_start_ws_client, daemon=True)
            self._ws_thread.start()
            
            logger.info("飞书机器人启动成功，开始监听消息...")
            
            # 等待停止信号
            while self._running and not self._stop_event.is_set():
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"启动飞书机器人失败: {e}, {traceback.format_exc()}")
            self._running = False
            raise
    
    def stop(self) -> None:
        """停止飞书机器人"""
        try:
            logger.info("正在停止飞书机器人...")
            self._running = False
            self._stop_event.set()
            
            # 停止 WebSocket 客户端
            if self.ws_client:
                try:
                    # 尝试不同的停止方法
                    if hasattr(self.ws_client, 'close'):
                        self.ws_client.close()
                        logger.debug("调用了 ws_client.close()")
                    elif hasattr(self.ws_client, 'disconnect'):
                        self.ws_client.disconnect()
                        logger.debug("调用了 ws_client.disconnect()")
                    elif hasattr(self.ws_client, 'shutdown'):
                        self.ws_client.shutdown()
                        logger.debug("调用了 ws_client.shutdown()")
                    
                    # 如果有内部停止事件，设置它
                    if hasattr(self.ws_client, '_stop_event'):
                        self.ws_client._stop_event.set()
                        logger.debug("设置了 ws_client._stop_event")
                        
                except Exception as ws_e:
                    logger.error(f"停止WebSocket客户端时出错: {ws_e}")
            
            # 等待WebSocket线程结束
            if self._ws_thread and self._ws_thread.is_alive():
                logger.info("等待WebSocket线程结束...")
                self._ws_thread.join(timeout=5.0)  # 最多等待5秒
                if self._ws_thread.is_alive():
                    logger.warning("WebSocket线程未能在5秒内结束")
                else:
                    logger.info("WebSocket线程已结束")
            
            logger.info("飞书机器人已停止")
            
        except Exception as e:
            logger.error(f"停止飞书机器人失败: {e}, {traceback.format_exc()}")
    
    def _process_message_in_thread(self, data: P2ImMessageReceiveV1) -> None:
        """在单独的线程中处理接收到的消息"""
        try:
            # 解析消息内容
            message_content = ""
            if data.event.message.message_type == "text":
                message_content = json.loads(data.event.message.content)["text"]
            else:
                self._send_response(data, "抱歉，我只能处理文本消息，请发送文本消息。")
                return
            
            logger.info(f"收到飞书消息: {message_content}")
            
            # 处理消息并生成响应
            response_content = self._process_message(message_content)
            
            # 发送响应
            self._send_response(data, response_content)
            
        except Exception as e:
            logger.error(f"处理飞书消息失败: {e}, {traceback.format_exc()}")
            self._send_response(data, f"处理消息时发生错误: {str(e)}")

    def _handle_message(self, data: P2ImMessageReceiveV1) -> None:
        """处理接收到的消息，将其放入新线程中执行以避免阻塞"""
        thread = threading.Thread(target=self._process_message_in_thread, args=(data,))
        thread.daemon = True
        thread.start()
    
    def _process_message(self, message: str) -> str:
        """处理消息并生成响应
        
        Args:
            message: 用户发送的消息
            
        Returns:
            响应内容
        """
        try:
            message = message.strip()
            
            # 获取可用策略列表
            if "获取可用策略列表" in message or "策略列表" in message:
                return self._get_available_strategies()
            
            # 根据策略ID筛选股票
            strategy_match = re.search(r"根据id为(\d+)的策略筛选股票", message)
            if strategy_match:
                strategy_id = int(strategy_match.group(1))
                return self._screen_stocks_by_strategy(strategy_id)

            # 获取策略详情
            detail_match = re.search(r"获取策略(\d+)详情", message)
            if detail_match:
                strategy_id = int(detail_match.group(1))
                return self._get_strategy_detail(strategy_id)
            
            # 帮助信息
            if "帮助" in message or "help" in message.lower():
                return self._get_help_message()
            
            # 未知指令
            return "❓ 抱歉，我不理解您的指令。\n\n" \
                   "💡 **可用指令:**\n" \
                   "• 获取可用策略列表\n" \
                   "• 根据id为X的策略筛选股票\n" \
                   "• 根据策略名称'XXX'筛选股票\n" \
                   "• 获取策略X详情\n" \
                   "• 帮助\n\n" \
                   "请发送正确的指令格式。"
            
        except Exception as e:
            logger.error(f"处理消息逻辑失败: {e}, {traceback.format_exc()}")
            return f"处理消息时发生错误: {str(e)}"
    
    def _get_available_strategies(self) -> str:
        """获取可用策略列表"""
        try:
            # 真实对象：需要异步调用
            future = asyncio.run_coroutine_threadsafe(self.strategy_manager.get_strategies(), self.loop)
            strategies = future.result()  # 等待结果
            available_strategies = [{'id': strategy.get("id", ""), 'name': strategy.get("name", "")} for strategy in strategies]
            logger.info(f"获取到的策略列表: {available_strategies}")
            if not available_strategies:
                return "当前没有可用的策略。"
            
            response = "📊 **可用策略列表**\n\n"
            for strategy in available_strategies:
                response += f"{strategy['id']}. {strategy['name']}\n"
            
            response += "\n💡 **使用提示:**\n"
            response += "• 发送 '根据id为1的策略筛选股票' 来使用策略筛选\n"
            response += "• 发送 '获取策略1详情' 来查看策略详情\n"
            response += "• 发送 '帮助' 查看更多功能"
            
            return response
            
        except Exception as e:
            logger.error(f"获取可用策略失败: {e}, {traceback.format_exc()}")
            return f"获取可用策略失败: {str(e)}"
    
    def _screen_stocks_by_strategy(self, strategy_id: int) -> str:
        """根据策略ID筛选股票"""
        try:
            # 真实对象：需要异步调用
            future = asyncio.run_coroutine_threadsafe(self.strategy_manager.get_strategy_detail(strategy_id), self.loop)
            strategy = future.result()  # 等待结果
            if not strategy:
                return f"❌ 策略ID {strategy_id} 不存在"
            strategy_name = strategy.get("name", f"策略{strategy_id}")

            # 调用股票筛选服务
            future = asyncio.run_coroutine_threadsafe(
                self.stock_screener.screen_stocks_by_strategy(
                    strategy_id=strategy_id,
                    stock_list=None,
                    date=None
                ),
                self.loop
            )
            result = future.result()

            if not result or not result.get('matched_stocks'):
                return f"❌ 使用策略 '{strategy_name}' 未筛选到符合条件的股票"
            
            stocks = result['matched_stocks'][:10]  # 只显示前10只
            
            response = f"📈 **策略筛选结果**\n\n"
            response += f"**策略名称:** {strategy_name}\n"
            response += f"**策略ID:** {strategy_id}\n"
            response += f"**筛选时间:** {result.get('timestamp', '未知')}\n"
            response += f"**符合条件股票数:** {len(result.get('matched_stocks', []))}\n\n"
            
            response += "**前10只股票:**\n"
            for i, stock in enumerate(stocks, 1):
                symbol = stock.get('symbol', '未知')
                name = stock.get('name', '未知')
                price = stock.get('price', 0)
                # change_pct = stock.get('change_percent', 0)
                
                # change_emoji = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
                response += f"{i}. {symbol} ({name}) 价格: ¥{price:.2f}\n"
                # response += f"   价格: ¥{price:.2f} {change_emoji} {change_pct:+.2f}%\n\n"
            
            if len(result.get('stocks', [])) > 10:
                response += f"... 还有 {len(result.get('stocks', [])) - 10} 只股票\n\n"
            
            response += "💡 **提示:** 发送 '帮助' 查看更多功能"
            
            return response
            
        except Exception as e:
            logger.error(f"根据策略筛选股票失败: {e}, {traceback.format_exc()}")
            return f"根据策略筛选股票失败: {str(e)}"
    
    def _get_strategy_detail(self, strategy_id: int) -> str:
        """获取策略详情"""
        try:
            # 真实对象：需要异步调用
            future = asyncio.run_coroutine_threadsafe(self.strategy_manager.get_strategy_detail(strategy_id), self.loop)
            strategy = future.result()  # 等待结果
        
            if not strategy:
                return f"❌ 策略ID {strategy_id} 不存在"

            
            response = f"📋 **策略详情**\n\n"
            response += f"**策略名称:** {strategy.get('name', '未知')}\n"
            response += f"**策略ID:** {strategy_id}\n"
            response += f"**策略类型:** {strategy.get('type', strategy.get('strategy_type', '未知'))}\n"
            response += f"**创建时间:** {strategy.get('created_at', '未知')}\n"
            response += f"**最后更新:** {strategy.get('updated_at', '未知')}\n\n"
            # for i, condition in enumerate(strategy.get('condition_details', [])):
            #     response += f"**条件{i+1}:** {condition.get('name', '未知')}\n"
            #     response += f"**参数:** {condition.get('parameters', '未知')}\n\n"
            
            # 策略描述
            description = strategy.get('description', '')
            if description:
                response += f"**策略描述:**\n{description}\n\n"
            
            # 策略参数
            parameters = strategy.get('parameters', {})
            if parameters:
                response += "**策略参数:**\n"
                for key, value in parameters.items():
                    response += f"• {key}: {value}\n"
                response += "\n"
            
            # 性能指标
            performance = strategy.get('performance', {})
            if performance:
                response += "**性能指标:**\n"
                response += f"• 年化收益率: {performance.get('annual_return', 'N/A')}\n"
                response += f"• 夏普比率: {performance.get('sharpe_ratio', 'N/A')}\n"
                response += f"• 最大回撤: {performance.get('max_drawdown', 'N/A')}\n"
                response += f"• 胜率: {performance.get('win_rate', 'N/A')}\n\n"
            
            response += "💡 **提示:** 发送 '根据id为X的策略筛选股票' 来使用此策略筛选股票"
            
            return response
            
        except Exception as e:
            logger.error(f"获取策略详情失败: {e}, {traceback.format_exc()}")
            return f"获取策略详情失败: {str(e)}"
    
    def _get_help_message(self) -> str:
        """获取帮助信息"""
        return """🤖 **智能量化交易助手**

📚 **可用功能:**

1️⃣ **策略管理**
• 获取可用策略列表
• 获取策略1详情

2️⃣ **股票筛选**
• 根据id为1的策略筛选股票
• 根据策略'策略名称'筛选股票

3️⃣ **其他功能**
• 帮助 - 显示此帮助信息

💡 **使用示例:**
• "获取可用策略列表"
• "根据id为1的策略筛选股票"
• "获取策略1详情"

如有问题，请联系系统管理员。"""
    
    def _get_default_response(self) -> str:
        """获取默认响应"""
        return """👋 您好！我是智能量化交易助手。

我可以帮您:
• 查看可用策略列表
• 根据策略筛选股票
• 获取策略详情

发送 "帮助" 查看详细功能说明。"""
    
    def _send_response(self, data: P2ImMessageReceiveV1, content: str) -> None:
        """发送响应消息
        
        Args:
            data: 接收到的消息数据
            content: 响应内容
        """
        try:
            response_content = json.dumps({"text": content})
            
            if data.event.message.chat_type == "p2p":
                # 私聊消息
                request = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(
                        CreateMessageRequestBody.builder()
                        .receive_id(data.event.message.chat_id)
                        .msg_type("text")
                        .content(response_content)
                        .build()
                    )
                    .build()
                )
                
                response = self.client.im.v1.chat.create(request)
                
                if not response.success():
                    logger.error(
                        f"发送私聊消息失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
                    )
            else:
                # 群聊消息，使用回复
                request = (
                    ReplyMessageRequest.builder()
                    .message_id(data.event.message.message_id)
                    .request_body(
                        ReplyMessageRequestBody.builder()
                        .content(response_content)
                        .msg_type("text")
                        .build()
                    )
                    .build()
                )
                
                response = self.client.im.v1.message.reply(request)
                
                if not response.success():
                    logger.error(
                        f"回复群聊消息失败, code: {response.code}, msg: {response.msg}, log_id: {response.get_log_id()}"
                    )
            
            logger.info(f"成功发送飞书响应: {content[:100]}...")
            
        except Exception as e:
            logger.error(f"发送飞书响应失败: {e}, {traceback.format_exc()}")