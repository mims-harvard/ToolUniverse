#!/usr/bin/env python3
"""
Human Expert MCP Tools - Refactored with @register_mcp_tool
==========================================================

This module contains human expert consultation tools that have been refactored
to use the new @register_mcp_tool decorator system instead of FastMCP.

Tools available:
- consult_human_expert: Submit questions to human scientific experts
- get_expert_response: Check for expert responses
- list_pending_expert_requests: View pending requests (for experts)
- submit_expert_response: Submit expert responses (for experts)
- get_expert_status: Get system status

Usage:
    from tooluniverse.mcp_tool_registry import start_mcp_server
    # Tools are automatically registered and available on startup
"""

import threading
import time
import uuid
import argparse
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Timer
from typing import Dict, List, Optional, Any

# Import the new registration system
from tooluniverse.mcp_tool_registry import register_mcp_tool, start_mcp_server
import requests

# Check Flask availability for web interface
try:
    from flask import Flask, render_template_string, request, jsonify, redirect, url_for

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# =============================================================================
#  HUMAN EXPERT SYSTEM (Same as original)
# =============================================================================


class HumanExpertSystem:
    """
    Expert consultation system for human-in-the-loop scientific decision support.

    This system manages the flow of expert consultation requests:
    1. Receives consultation requests from tools/agents
    2. Queues requests for human expert review
    3. Provides interfaces for experts to respond
    4. Returns expert responses to requesting tools
    """

    def __init__(
        self,
        expert_name: str = "Scientific Expert",
        specialty: str = "General Medicine",
    ):
        """Initialize the expert system"""

        # Expert information
        self.expert_info = {
            "name": expert_name,
            "specialty": specialty,
            "status": "available",
            "last_activity": datetime.now().isoformat(),
        }

        # Request management
        self.pending_requests: List[Dict] = []  # Requests waiting for expert response
        self.responses: Dict[str, Dict] = {}  # Completed expert responses
        self.request_status: Dict[str, str] = {}  # Request status tracking

        # Thread safety
        self.lock = threading.Lock()

        print("🧑‍⚕️ Human Expert System Initialized")
        print(f"   👨‍⚕️ Expert: {expert_name} ({specialty})")
        print("   🔄 Status: Ready for consultation requests")

    def submit_request(
        self, request_id: str, question: str, context: Optional[Dict] = None
    ) -> None:
        """Submit a new expert consultation request"""

        request_data = {
            "id": request_id,
            "question": question,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
        }

        with self.lock:
            self.pending_requests.append(request_data)
            self.request_status[request_id] = "pending"

        print(f"📝 New expert request submitted: {request_id}")
        print(f"   ❓ Question: {question[:100]}{'...' if len(question) > 100 else ''}")

        if context:
            print(f"   🎯 Specialty: {context.get('specialty', 'general')}")
            print(f"   ⚡ Priority: {context.get('priority', 'normal')}")

    def get_pending_requests(self) -> List[Dict]:
        """Get all pending expert consultation requests"""
        with self.lock:
            return self.pending_requests.copy()

    def submit_response(self, request_id: str, response: str) -> bool:
        """Submit expert response to a consultation request"""

        with self.lock:
            # Find and remove the request from pending
            for i, req in enumerate(self.pending_requests):
                if req["id"] == request_id:
                    request_data = self.pending_requests.pop(i)

                    # Store the response
                    self.responses[request_id] = {
                        "request": request_data,
                        "response": response,
                        "expert": self.expert_info["name"],
                        "timestamp": datetime.now().isoformat(),
                    }

                    # Update status
                    self.request_status[request_id] = "completed"
                    self.expert_info["last_activity"] = datetime.now().isoformat()

                    print(f"✅ Expert response submitted for request: {request_id}")
                    return True

            return False

    def get_response(
        self, request_id: str, timeout_seconds: int = 300
    ) -> Optional[Dict]:
        """Wait for and retrieve expert response"""

        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            with self.lock:
                if request_id in self.responses:
                    return self.responses[request_id]

            time.sleep(1)  # Check every second

        return None  # Timeout


# Initialize global expert system
expert_system = HumanExpertSystem()

# Thread executor for async operations
executor = ThreadPoolExecutor(max_workers=4)

# =============================================================================
# 🧰 MCP TOOL REGISTRATION (Following tutorial standards)
# =============================================================================


# Register Human Expert Consultation Tool
@register_mcp_tool(
    tool_type_name="consult_human_expert",
    config={
        "description": "Consult a human expert for complex scientific questions requiring human judgment",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The scientific question or case requiring expert consultation",
                },
                "specialty": {
                    "type": "string",
                    "default": "general",
                    "description": "Area of expertise needed (e.g., 'cardiology', 'oncology', 'pharmacology')",
                },
                "priority": {
                    "type": "string",
                    "default": "normal",
                    "enum": ["low", "normal", "high", "urgent"],
                    "description": "Request priority",
                },
                "context": {
                    "type": "string",
                    "default": "",
                    "description": "Additional context or background information",
                },
                "timeout_minutes": {
                    "type": "integer",
                    "default": 5,
                    "description": "How long to wait for expert response (default: 5 minutes)",
                },
            },
            "required": ["question"],
        },
    },
    mcp_config={
        "server_name": "Human Expert Consultation Server",
        "host": "0.0.0.0",
        "port": 9876,
    },
)
class ConsultHumanExpertTool:
    """
    Consult a human expert for complex scientific questions requiring human judgment.

    This tool submits questions to human scientific experts who can provide:
    - Clinical decision support
    - Drug interaction analysis validation
    - Treatment recommendation review
    - Complex case interpretation
    - Quality assurance for AI recommendations
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute human expert consultation"""

        # Extract parameters
        question_any = arguments.get("question")
        if not isinstance(question_any, str) or not question_any:
            return {"status": "error", "error": "'question' must be a non-empty string"}
        question = question_any
        specialty = arguments.get("specialty", "general")
        priority = arguments.get("priority", "normal")
        context = arguments.get("context", "")
        timeout_minutes = arguments.get("timeout_minutes", 5)

        request_id = str(uuid.uuid4())[:8]
        timeout_seconds = timeout_minutes * 60

        print(f"\n🔔 EXPERT CONSULTATION REQUEST [{request_id}]")
        print(f"🎯 Specialty: {specialty}")
        print(f"⚡ Priority: {priority}")
        print(f"⏱️ Timeout: {timeout_minutes} minutes")

        try:
            # Submit request to expert system
            context_data = {
                "specialty": specialty,
                "priority": priority,
                "context": context,
            }

            expert_system.submit_request(request_id, question, context_data)

            # Wait for expert response
            print(f"⏳ Waiting for expert response (max {timeout_minutes} minutes)...")

            response_data = expert_system.get_response(request_id, timeout_seconds)

            if response_data:
                return {
                    "status": "completed",
                    "expert_response": response_data["response"],
                    "expert_name": response_data["expert"],
                    "response_time": response_data["timestamp"],
                    "request_id": request_id,
                    "specialty": specialty,
                    "priority": priority,
                }
            else:
                return {
                    "status": "timeout",
                    "message": f"No expert response received within {timeout_minutes} minutes",
                    "request_id": request_id,
                    "note": "Request may still be processed. Check with get_expert_response tool later.",
                }

        except Exception as e:
            print(f"❌ Expert consultation failed: {str(e)}")
            return {
                "status": "error",
                "error": f"Expert consultation failed: {str(e)}",
                "request_id": request_id,
            }


# Register Get Expert Response Tool
@register_mcp_tool(
    tool_type_name="get_expert_response",
    config={
        "description": "Check if an expert response is available for a previous request",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "The ID of the expert consultation request",
                }
            },
            "required": ["request_id"],
        },
    },
    mcp_config={"port": 9876},  # Same server as consultation tool
)
class GetExpertResponseTool:
    """Tool to check if an expert response is available for a previous request."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check for expert response"""

        request_id = arguments.get("request_id")

        try:
            with expert_system.lock:
                if request_id in expert_system.responses:
                    response_data = expert_system.responses[request_id]
                    return {
                        "status": "completed",
                        "expert_response": response_data["response"],
                        "expert_name": response_data["expert"],
                        "response_time": response_data["timestamp"],
                        "request_id": request_id,
                    }
                elif request_id in expert_system.request_status:
                    status = expert_system.request_status[request_id]
                    return {
                        "status": status,
                        "message": f"Request {request_id} is {status}",
                        "request_id": request_id,
                    }
                else:
                    return {
                        "status": "not_found",
                        "message": f"Request {request_id} not found",
                        "request_id": request_id,
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to check expert response: {str(e)}",
                "request_id": request_id,
            }


# Register List Pending Expert Requests Tool
@register_mcp_tool(
    tool_type_name="list_pending_expert_requests",
    config={
        "description": "List all pending expert consultation requests (for expert use)",
        "parameter_schema": {"type": "object", "properties": {}, "required": []},
    },
    mcp_config={"port": 9876},  # Same server
)
class ListPendingExpertRequestsTool:
    """Tool to list all pending expert consultation requests (for expert use)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List pending expert requests"""

        try:
            pending = expert_system.get_pending_requests()

            if not pending:
                return {
                    "status": "no_requests",
                    "message": "No pending expert requests",
                    "count": 0,
                }

            requests_summary = []
            for req in pending:
                age_seconds = (
                    datetime.now() - datetime.fromisoformat(req["timestamp"])
                ).total_seconds()
                requests_summary.append(
                    {
                        "request_id": req["id"],
                        "question": req["question"],
                        "specialty": req.get("context", {}).get("specialty", "general"),
                        "priority": req.get("context", {}).get("priority", "normal"),
                        "age_minutes": round(age_seconds / 60, 1),
                        "timestamp": req["timestamp"],
                    }
                )

            return {
                "status": "success",
                "pending_requests": requests_summary,
                "count": len(requests_summary),
                "expert_info": expert_system.expert_info,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to list pending requests: {str(e)}",
            }


# Register Submit Expert Response Tool
@register_mcp_tool(
    tool_type_name="submit_expert_response",
    config={
        "description": "Submit expert response to a consultation request (for expert use)",
        "parameter_schema": {
            "type": "object",
            "properties": {
                "request_id": {
                    "type": "string",
                    "description": "The ID of the request to respond to",
                },
                "response": {
                    "type": "string",
                    "description": "The expert's response and recommendations",
                },
            },
            "required": ["request_id", "response"],
        },
    },
    mcp_config={"port": 9876},  # Same server
)
class SubmitExpertResponseTool:
    """Tool to submit expert response to a consultation request (for expert use)."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Submit expert response"""

        request_id_any = arguments.get("request_id")
        response_any = arguments.get("response")
        if not isinstance(request_id_any, str) or not isinstance(response_any, str):
            return {
                "status": "error",
                "error": "'request_id' and 'response' must be strings",
            }
        request_id = request_id_any
        response = response_any

        try:
            success = expert_system.submit_response(request_id, response)

            if success:
                return {
                    "status": "success",
                    "message": f"Expert response submitted for request {request_id}",
                    "request_id": request_id,
                    "expert": expert_system.expert_info["name"],
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "failed",
                    "message": f"Request {request_id} not found or already completed",
                    "request_id": request_id,
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to submit expert response: {str(e)}",
                "request_id": request_id,
            }


# Register Get Expert Status Tool
@register_mcp_tool(
    tool_type_name="get_expert_status",
    config={
        "description": "Get current expert system status and statistics",
        "parameter_schema": {"type": "object", "properties": {}, "required": []},
    },
    mcp_config={"port": 9876},  # Same server
)
class GetExpertStatusTool:
    """Tool to get current expert system status and statistics."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expert system status"""

        try:
            pending = expert_system.get_pending_requests()

            with expert_system.lock:
                total_responses = len(expert_system.responses)
                total_requests = len(expert_system.request_status)

            return {
                "status": "active",
                "expert_info": expert_system.expert_info,
                "statistics": {
                    "pending_requests": len(pending),
                    "total_requests": total_requests,
                    "completed_responses": total_responses,
                    "response_rate": round(
                        total_responses / max(total_requests, 1) * 100, 1
                    ),
                },
                "system_time": datetime.now().isoformat(),
                "mcp_server_port": 9876,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get expert status: {str(e)}",
            }


# =============================================================================
# 🌐 HTTP API SERVER (Independent from Web Interface)
# =============================================================================


def create_http_api_server():
    """Create independent HTTP API server for expert system communication"""
    if not FLASK_AVAILABLE:
        return None

    api_app = Flask(__name__)

    @api_app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "expert_system": "active",
        }

    @api_app.route("/api/requests", methods=["GET"])
    def get_pending_requests():
        """Get all pending expert requests via HTTP API"""
        try:
            pending = expert_system.get_pending_requests()

            requests_summary = []
            for req in pending:
                age_seconds = (
                    datetime.now() - datetime.fromisoformat(req["timestamp"])
                ).total_seconds()
                requests_summary.append(
                    {
                        "request_id": req["id"],
                        "question": req["question"],
                        "specialty": req.get("context", {}).get("specialty", "general"),
                        "priority": req.get("context", {}).get("priority", "normal"),
                        "age_minutes": round(age_seconds / 60, 1),
                        "timestamp": req["timestamp"],
                        "context": req.get("context", {}),
                    }
                )

            with expert_system.lock:
                total_responses = len(expert_system.responses)
                total_requests = len(expert_system.request_status)

            return {
                "status": "success",
                "pending_requests": requests_summary,
                "count": len(requests_summary),
                "expert_info": expert_system.expert_info,
                "statistics": {
                    "pending_requests": len(pending),
                    "total_requests": total_requests,
                    "completed_responses": total_responses,
                    "response_rate": round(
                        total_responses / max(total_requests, 1) * 100, 1
                    ),
                },
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}, 500

    @api_app.route("/api/requests/<request_id>/respond", methods=["POST"])
    def submit_expert_response_api(request_id):
        """Submit expert response via HTTP API"""
        try:
            data = request.get_json()
            response_text = data.get("response", "").strip()

            if not response_text:
                return {"status": "error", "error": "Response text is required"}, 400

            success = expert_system.submit_response(request_id, response_text)

            if success:
                return {
                    "status": "success",
                    "message": f"Expert response submitted for request {request_id}",
                    "request_id": request_id,
                    "expert": expert_system.expert_info["name"],
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                return {
                    "status": "failed",
                    "error": f"Request {request_id} not found or already completed",
                }, 404

        except Exception as e:
            return {"status": "error", "error": str(e)}, 500

    @api_app.route("/api/status", methods=["GET"])
    def get_system_status():
        """Get expert system status via HTTP API"""
        try:
            pending = expert_system.get_pending_requests()

            with expert_system.lock:
                total_responses = len(expert_system.responses)
                total_requests = len(expert_system.request_status)

            return {
                "status": "active",
                "expert_info": expert_system.expert_info,
                "statistics": {
                    "pending_requests": len(pending),
                    "total_requests": total_requests,
                    "completed_responses": total_responses,
                    "response_rate": round(
                        total_responses / max(total_requests, 1) * 100, 1
                    ),
                },
                "system_time": datetime.now().isoformat(),
                "mcp_server_port": 9876,
                "api_server_port": 9877,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}, 500

    return api_app


# =============================================================================
# 🌐 WEB INTERFACE (Modified to use HTTP API)
# =============================================================================


def create_web_app():
    """Create Flask web application for expert interface"""
    if not FLASK_AVAILABLE:
        return None

    app = Flask(__name__)

    # Web interface HTML template with modern UI improvements
    WEB_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <title>🧑‍⚕️ ToolUniverse Human Expert Interface</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta charset="UTF-8">
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }

            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }

            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
                animation: slideUp 0.8s ease-out;
            }

            @keyframes slideUp {
                from { transform: translateY(30px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
            }

            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
                position: relative;
                overflow: hidden;
            }

            .header::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                animation: pulse 4s ease-in-out infinite;
            }

            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 0.5; }
                50% { transform: scale(1.1); opacity: 0.8; }
            }

            .header h1 {
                font-size: 2.5em;
                margin-bottom: 10px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                position: relative;
                z-index: 1;
            }

            .header p {
                font-size: 1.2em;
                opacity: 0.9;
                position: relative;
                z-index: 1;
            }

            .status-bar {
                background: #f8f9fa;
                padding: 15px 30px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 15px;
            }

            .status-indicator {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 8px 15px;
                background: white;
                border-radius: 25px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }

            .status-indicator:hover {
                transform: translateY(-2px);
            }

            .status-dot {
                width: 12px;
                height: 12px;
                border-radius: 50%;
                background: #28a745;
                animation: heartbeat 2s ease-in-out infinite;
            }

            .status-dot.online {
                background: #28a745;
                animation: heartbeat 2s ease-in-out infinite;
            }

            .status-dot.offline {
                background: #ffc107;
                animation: blink 1.5s ease-in-out infinite;
            }

            @keyframes heartbeat {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.1); }
            }

            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            .auto-refresh {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9em;
                color: #6c757d;
            }

            .refresh-countdown {
                background: #667eea;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-weight: bold;
                min-width: 30px;
                text-align: center;
            }

            .main-content {
                padding: 30px;
            }

            .section {
                margin: 30px 0;
                padding: 25px;
                border: 1px solid #e9ecef;
                border-radius: 15px;
                background: white;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                transition: transform 0.2s, box-shadow 0.2s;
            }

            .section:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }

            .section h2 {
                margin-bottom: 20px;
                color: #495057;
                border-bottom: 2px solid #667eea;
                padding-bottom: 10px;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 25px 0;
            }

            .stat {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 15px;
                text-align: center;
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3);
                transition: transform 0.3s, box-shadow 0.3s;
                position: relative;
                overflow: hidden;
            }

            .stat::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
                transform: scale(0);
                transition: transform 0.3s;
            }

            .stat:hover::before {
                transform: scale(1);
            }

            .stat:hover {
                transform: translateY(-5px) scale(1.02);
                box-shadow: 0 15px 30px rgba(102, 126, 234, 0.4);
            }

            .stat h3 {
                font-size: 2.5em;
                margin-bottom: 10px;
                position: relative;
                z-index: 1;
            }

            .stat p {
                font-size: 1.1em;
                opacity: 0.9;
                position: relative;
                z-index: 1;
            }

            .expert-info {
                background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                color: white;
                padding: 20px;
                border-radius: 15px;
                margin-top: 20px;
                display: flex;
                align-items: center;
                gap: 15px;
            }

            .expert-avatar {
                width: 60px;
                height: 60px;
                background: rgba(255,255,255,0.2);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.5em;
            }

            .request {
                background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
                margin: 20px 0;
                padding: 25px;
                border-left: 5px solid #667eea;
                border-radius: 15px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.08);
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .request::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(90deg, #667eea, #764ba2);
                opacity: 0;
                transition: opacity 0.3s;
            }

            .request:hover::before {
                opacity: 1;
            }

            .request:hover {
                transform: translateY(-3px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.15);
            }

            .priority-high { border-left-color: #fd7e14; }
            .priority-urgent {
                border-left-color: #dc3545;
                background: linear-gradient(135deg, #fff5f5 0%, #ffffff 100%);
                animation: urgentPulse 2s infinite;
            }

            @keyframes urgentPulse {
                0%, 100% { box-shadow: 0 5px 15px rgba(0,0,0,0.08); }
                50% { box-shadow: 0 10px 25px rgba(220, 53, 69, 0.2); }
            }

            .question {
                font-weight: 600;
                margin: 15px 0;
                font-size: 1.1em;
                color: #495057;
                line-height: 1.5;
            }

            .context {
                color: #6c757d;
                margin: 15px 0;
                padding: 15px;
                background: rgba(108, 117, 125, 0.05);
                border-radius: 10px;
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                align-items: center;
            }

            .context-item {
                display: flex;
                align-items: center;
                gap: 5px;
                padding: 5px 10px;
                background: white;
                border-radius: 15px;
                font-size: 0.9em;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }

            .timestamp {
                color: #adb5bd;
                font-size: 0.85em;
                margin-top: 10px;
                display: flex;
                align-items: center;
                gap: 5px;
            }

            .response-form {
                margin-top: 20px;
                padding: 20px;
                background: rgba(102, 126, 234, 0.02);
                border-radius: 12px;
                border: 1px dashed #667eea;
            }

            textarea {
                width: 100%;
                min-height: 120px;
                padding: 15px;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                resize: vertical;
                font-family: inherit;
                font-size: 1em;
                line-height: 1.5;
                transition: border-color 0.3s, box-shadow 0.3s;
            }

            textarea:focus {
                outline: none;
                border-color: #667eea;
                box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            }

            button {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 12px 25px;
                border-radius: 25px;
                cursor: pointer;
                font-size: 1em;
                font-weight: 600;
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
            }

            button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            }

            button:active {
                transform: translateY(0);
            }

            .no-requests {
                text-align: center;
                padding: 60px 20px;
                color: #6c757d;
            }

            .no-requests i {
                font-size: 4em;
                margin-bottom: 20px;
                color: #28a745;
            }

            .instructions {
                background: linear-gradient(135deg, #17a2b8 0%, #138496 100%);
                color: white;
                border-radius: 15px;
                padding: 25px;
            }

            .instructions ul {
                list-style: none;
                padding: 0;
            }

            .instructions li {
                padding: 8px 0;
                display: flex;
                align-items: center;
                gap: 10px;
            }

            .instructions li::before {
                content: '✓';
                background: rgba(255,255,255,0.2);
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: bold;
            }

            .loading {
                display: none;
                text-align: center;
                padding: 20px;
                color: #6c757d;
            }

            .loading i {
                animation: spin 1s linear infinite;
            }

            @keyframes spin {
                from { transform: rotate(0deg); }
                to { transform: rotate(360deg); }
            }

            /* Responsive design */
            @media (max-width: 768px) {
                body { padding: 10px; }
                .container { border-radius: 10px; }
                .header { padding: 20px; }
                .header h1 { font-size: 2em; }
                .main-content { padding: 20px; }
                .section { padding: 15px; }
                .stats { grid-template-columns: 1fr; }
                .context { flex-direction: column; align-items: flex-start; }
                .status-bar { flex-direction: column; }
            }

            /* Notification styles */
            .notification {
                position: fixed;
                top: 20px;
                right: 20px;
                background: #28a745;
                color: white;
                padding: 15px 20px;
                border-radius: 10px;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                transform: translateX(400px);
                transition: transform 0.3s;
                z-index: 1000;
            }

            .notification.show {
                transform: translateX(0);
            }
        </style>
        <script>
            let countdownInterval;
            let refreshInterval = 15; // 15 seconds instead of 30
            let currentCountdown = refreshInterval;

            function updateCountdown() {
                const countdownEl = document.getElementById('countdown');
                if (countdownEl) {
                    countdownEl.textContent = currentCountdown;
                    currentCountdown--;

                    if (currentCountdown < 0) {
                        currentCountdown = refreshInterval;
                        refreshPage();
                    }
                }
            }

            function refreshPage() {
                const loadingEl = document.querySelector('.loading');
                if (loadingEl) {
                    loadingEl.style.display = 'block';
                }

                // Add a small delay to show loading animation
                setTimeout(() => {
                    location.reload();
                }, 500);
            }

            function startAutoRefresh() {
                // Update countdown every second
                countdownInterval = setInterval(updateCountdown, 1000);

                // Show notification on first load
                showNotification('Auto-refresh enabled: Updates every ' + refreshInterval + ' seconds', 'info');
            }

            function showNotification(message, type = 'success') {
                const notification = document.createElement('div');
                notification.className = 'notification';
                notification.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i> ${message}`;
                document.body.appendChild(notification);

                setTimeout(() => notification.classList.add('show'), 100);
                setTimeout(() => {
                    notification.classList.remove('show');
                    setTimeout(() => notification.remove(), 300);
                }, 3000);
            }

            function submitResponse(form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

                // Let the form submit naturally
                return true;
            }

            // Initialize when page loads
            window.addEventListener('load', function() {
                startAutoRefresh();

                // Add click handlers to forms
                document.querySelectorAll('.response-form').forEach(form => {
                    form.addEventListener('submit', function() {
                        return submitResponse(this);
                    });
                });
            });

            // Handle page visibility changes (pause refresh when tab is not active)
            document.addEventListener('visibilitychange', function() {
                if (document.hidden) {
                    clearInterval(countdownInterval);
                } else {
                    currentCountdown = refreshInterval;
                    startAutoRefresh();
                }
            });
        </script>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1><i class="fas fa-user-md"></i> Human Expert Interface</h1>
                <p>ToolUniverse Scientific Consultation Response System</p>
            </div>

            <div class="status-bar">
                <div class="status-indicator">
                    <div class="status-dot"></div>
                    <span><strong>System Active</strong></span>
                </div>
                <div class="status-indicator">
                    <div class="status-dot {{ 'online' if mcp_info.connected else 'offline' }}"></div>
                    <span><strong>MCP: {{ mcp_info.host }}:{{ mcp_info.port }}</strong></span>
                    <span class="status-text">({{ 'Connected' if mcp_info.connected else 'Local Mode' }})</span>
                </div>
                <div class="auto-refresh">
                    <i class="fas fa-sync-alt"></i>
                    <span>Auto-refresh in</span>
                    <span class="refresh-countdown" id="countdown">{{ refreshInterval|default(15) }}</span>
                    <span>seconds</span>
                </div>
                <div class="status-indicator">
                    <i class="fas fa-clock"></i>
                    <span id="current-time"></span>
                </div>
            </div>

            <div class="main-content">
                <div class="section">
                    <h2><i class="fas fa-chart-bar"></i> System Status</h2>
                    <div class="stats">
                        <div class="stat">
                            <h3>{{ status.statistics.pending_requests }}</h3>
                            <p>Pending Requests</p>
                        </div>
                        <div class="stat">
                            <h3>{{ status.statistics.total_requests }}</h3>
                            <p>Total Requests</p>
                        </div>
                        <div class="stat">
                            <h3>{{ status.statistics.response_rate }}%</h3>
                            <p>Response Rate</p>
                        </div>
                    </div>
                    <div class="expert-info">
                        <div class="expert-avatar">
                            <i class="fas fa-user-md"></i>
                        </div>
                        <div>
                            <strong>{{ status.expert_info.name }}</strong><br>
                            <span>{{ status.expert_info.specialty }}</span>
                        </div>
                    </div>
                </div>

                <div class="section">
                    <h2><i class="fas fa-clipboard-list"></i> Pending Consultation Requests</h2>
                    {% if requests.count == 0 %}
                        <div class="no-requests">
                            <i class="fas fa-check-circle"></i>
                            <h3>All caught up!</h3>
                            <p>No pending requests at this time</p>
                        </div>
                    {% else %}
                        <p><strong>{{ requests.count }}</strong> request(s) waiting for expert response:</p>
                        {% for req in requests.pending_requests %}
                            <div class="request {% if req.priority == 'high' %}priority-high{% elif req.priority == 'urgent' %}priority-urgent{% endif %}">
                                <div class="question">
                                    <i class="fas fa-question-circle"></i> {{ req.question }}
                                </div>
                                <div class="context">
                                    <div class="context-item">
                                        <i class="fas fa-stethoscope"></i>
                                        <strong>Specialty:</strong> {{ req.specialty }}
                                    </div>
                                    <div class="context-item">
                                        <i class="fas fa-exclamation-triangle"></i>
                                        <strong>Priority:</strong> {{ req.priority }}
                                    </div>
                                    <div class="context-item">
                                        <i class="fas fa-clock"></i>
                                        <strong>Age:</strong> {{ req.age_minutes }} minutes
                                    </div>
                                </div>
                                <div class="timestamp">
                                    <i class="fas fa-calendar-alt"></i>
                                    {{ req.timestamp }}
                                </div>

                                <form method="POST" action="/submit_response" class="response-form">
                                    <input type="hidden" name="request_id" value="{{ req.request_id }}">
                                    <textarea name="response" placeholder="Enter your expert response and clinical recommendations here..." required></textarea>
                                    <button type="submit">
                                        <i class="fas fa-paper-plane"></i>
                                        Submit Expert Response
                                    </button>
                                </form>
                            </div>
                        {% endfor %}
                    {% endif %}
                </div>

                <div class="section instructions">
                    <h2><i class="fas fa-info-circle"></i> Instructions</h2>
                    <ul>
                        <li>This page auto-refreshes every 15 seconds for real-time updates</li>
                        <li>Review each consultation request carefully</li>
                        <li>Provide detailed clinical recommendations</li>
                        <li>Prioritize urgent and high-priority requests</li>
                        <li>All responses are logged and timestamped</li>
                    </ul>
                </div>

                <div class="loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Refreshing data...</p>
                </div>
            </div>
        </div>

        <script>
            // Update current time
            function updateTime() {
                const now = new Date();
                const timeStr = now.toLocaleTimeString();
                const timeEl = document.getElementById('current-time');
                if (timeEl) {
                    timeEl.textContent = timeStr;
                }
            }

            // Update time immediately and then every second
            updateTime();
            setInterval(updateTime, 1000);
        </script>
    </body>
    </html>
    """

    @app.route("/")
    def index():
        """Main expert interface page"""
        try:
            # Get HTTP API server URL from environment or default to localhost
            import os

            api_host = os.getenv("EXPERT_FEEDBACK_API_HOST", "localhost")
            api_port = os.getenv("EXPERT_FEEDBACK_API_PORT", "9877")
            api_url = f"http://{api_host}:{api_port}/api/requests"
            api_connected = False

            try:
                # Get pending requests from HTTP API server

                response = requests.get(api_url, timeout=5)

                if response.status_code == 200:
                    api_data = response.json()
                    api_connected = True

                    status = {
                        "expert_info": api_data.get(
                            "expert_info",
                            {
                                "name": "Scientific Expert",
                                "specialty": "General Medicine",
                            },
                        ),
                        "statistics": api_data.get(
                            "statistics",
                            {
                                "pending_requests": 0,
                                "total_requests": 0,
                                "completed_responses": 0,
                                "response_rate": 0.0,
                            },
                        ),
                    }

                    requests_data = {
                        "pending_requests": api_data.get("pending_requests", []),
                        "count": api_data.get("count", 0),
                    }

                else:
                    print(f"⚠️  HTTP API returned status {response.status_code}")
                    api_connected = False

            except requests.exceptions.ConnectinError:
                print(f"⚠️  Cannot connect to HTTP API server at {api_host}:{api_port}")
                api_connected = False
            except requests.exceptions.Timeout:
                print(f"⚠️  HTTP API server timeout at {api_host}:{api_port}")
                api_connected = False
            except Exception as e:
                print(f"⚠️  Error connecting to HTTP API server: {e}")
                api_connected = False

            # If API connection failed, show error page
            if not api_connected:
                status = {
                    "expert_info": {
                        "name": "Connection Error",
                        "specialty": f"Cannot connect to API server at {api_host}:{api_port}",
                    },
                    "statistics": {
                        "pending_requests": 0,
                        "total_requests": 0,
                        "completed_responses": 0,
                        "response_rate": 0.0,
                    },
                }

                requests_data = {
                    "pending_requests": [],
                    "count": 0,
                    "connection_error": True,
                }

            # Add API connection info
            api_info = {
                "host": api_host,
                "port": api_port,
                "url": api_url,
                "connected": api_connected,
            }

            return render_template_string(
                WEB_TEMPLATE, status=status, requests=requests_data, mcp_info=api_info
            )

        except Exception as e:
            return f"Error loading interface: {str(e)}", 500

    @app.route("/submit_response", methods=["POST"])
    def submit_response():
        """Handle expert response submission via HTTP API"""
        try:
            import os

            request_id = request.form.get("request_id")
            response_text = request.form.get("response")

            if not request_id or not response_text:
                return "Missing request ID or response", 400

            # Get HTTP API server URL
            api_host = os.getenv("EXPERT_FEEDBACK_API_HOST", "localhost")
            api_port = os.getenv("EXPERT_FEEDBACK_API_PORT", "9877")
            api_url = f"http://{api_host}:{api_port}/api/requests/{request_id}/respond"

            # Submit response via HTTP API
            payload = {"response": response_text}
            headers = {"Content-Type": "application/json"}

            try:
                api_response = requests.post(
                    api_url, json=payload, headers=headers, timeout=10
                )

                if api_response.status_code == 200:
                    print(
                        f"✅ Web interface: Expert response submitted via API for {request_id}"
                    )
                    return redirect(url_for("index"))
                else:
                    print(
                        f"⚠️  API submission failed: {api_response.status_code} - {api_response.text}"
                    )
                    return f"API Error: {api_response.status_code}", 500

            except requests.exceptions.ConnectinError:
                return "Cannot connect to API server", 503
            except requests.exceptions.Timeout:
                return "API server timeout", 504
            except Exception as e:
                print(f"⚠️  Error submitting via API: {e}")
                return f"Submission failed: {str(e)}", 500

        except Exception as e:
            return f"Error: {str(e)}", 500

    @app.route("/api/status")
    def api_status():
        """API endpoint for status information"""
        try:
            pending = expert_system.get_pending_requests()

            with expert_system.lock:
                total_responses = len(expert_system.responses)
                total_requests = len(expert_system.request_status)

            return jsonify(
                {
                    "status": "active",
                    "expert_info": expert_system.expert_info,
                    "statistics": {
                        "pending_requests": len(pending),
                        "total_requests": total_requests,
                        "completed_responses": total_responses,
                        "response_rate": round(
                            total_responses / max(total_requests, 1) * 100, 1
                        ),
                    },
                    "system_time": datetime.now().isoformat(),
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


# =============================================================================
# 💻 TERMINAL INTERFACE (Same as original)
# =============================================================================


class ExpertInterface:
    """Terminal-based expert interface for responding to consultation requests"""

    def __init__(self):
        self.running = True

    def display_banner(self):
        """Display welcome banner"""
        print("\n" + "=" * 80)
        print("🧑‍⚕️ HUMAN EXPERT TERMINAL INTERFACE")
        print("=" * 80)
        print(f"👨‍⚕️ Expert: {expert_system.expert_info['name']}")
        print(f"🎯 Specialty: {expert_system.expert_info['specialty']}")
        print(f"🕒 System Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

    def display_menu(self):
        """Display main menu options"""
        print("\n📋 EXPERT ACTIONS:")
        print("  1️⃣  View Pending Consultation Requests")
        print("  2️⃣  Respond to Specific Request")
        print("  3️⃣  View System Status")
        print("  4️⃣  View Recent Responses")
        print("  🔄  Auto-refresh (every 30 seconds)")
        print("  ❌  Quit")
        print("-" * 50)

    def view_pending_requests(self):
        """Display all pending consultation requests"""
        pending = expert_system.get_pending_requests()

        if not pending:
            print("\n✅ No pending consultation requests!")
            return

        print(f"\n📋 PENDING CONSULTATION REQUESTS ({len(pending)}):")
        print("=" * 80)

        for i, req in enumerate(pending, 1):
            age_seconds = (
                datetime.now() - datetime.fromisoformat(req["timestamp"])
            ).total_seconds()
            age_minutes = round(age_seconds / 60, 1)

            specialty = req.get("context", {}).get("specialty", "general")
            priority = req.get("context", {}).get("priority", "normal")

            print(f"\n[{i}] REQUEST ID: {req['id']}")
            print(
                f"🎯 Specialty: {specialty} | ⚡ Priority: {priority} | ⏰ Age: {age_minutes} min"
            )
            print(f"❓ Question: {req['question']}")

            if req.get("context", {}).get("context"):
                print(f"📝 Context: {req['context']['context']}")

            print(f"📅 Submitted: {req['timestamp']}")
            print("-" * 50)

    def respond_to_request(self):
        """Handle expert response to a specific request"""
        pending = expert_system.get_pending_requests()

        if not pending:
            print("\n✅ No pending requests to respond to!")
            return

        # Show pending requests
        self.view_pending_requests()

        # Get request selection
        try:
            choice = input(f"\nSelect request (1-{len(pending)}) or 'back': ").strip()

            if choice.lower() == "back":
                return

            request_idx = int(choice) - 1
            if request_idx < 0 or request_idx >= len(pending):
                print("❌ Invalid selection!")
                return

            selected_request = pending[request_idx]
            request_id = selected_request["id"]

            print(f"\n📝 RESPONDING TO REQUEST: {request_id}")
            print(f"❓ Question: {selected_request['question']}")
            print(
                "\n💡 Enter your expert response (type 'END' on a new line when finished):"
            )

            # Multi-line response input
            response_lines = []
            while True:
                line = input()
                if line.strip() == "END":
                    break
                response_lines.append(line)

            response = "\n".join(response_lines).strip()

            if not response:
                print("❌ Empty response! Response not submitted.")
                return

            # Confirm before submitting
            print("\n📋 RESPONSE PREVIEW:")
            print("-" * 40)
            print(response)
            print("-" * 40)

            confirm = input("\nSubmit this response? (y/N): ").strip().lower()

            if confirm == "y":
                success = expert_system.submit_response(request_id, response)
                if success:
                    print(
                        f"✅ Response submitted successfully for request {request_id}"
                    )
                else:
                    print(f"❌ Failed to submit response for request {request_id}")
            else:
                print("❌ Response cancelled.")

        except ValueError:
            print("❌ Invalid input! Please enter a number.")
        except KeyboardInterrupt:
            print("\n❌ Response cancelled.")

    def view_system_status(self):
        """Display system status and statistics"""
        pending = expert_system.get_pending_requests()

        with expert_system.lock:
            total_responses = len(expert_system.responses)
            total_requests = len(expert_system.request_status)

        print("\n📊 EXPERT SYSTEM STATUS:")
        print("=" * 50)
        print(f"👨‍⚕️ Expert: {expert_system.expert_info['name']}")
        print(f"🎯 Specialty: {expert_system.expert_info['specialty']}")
        print(f"📊 Pending Requests: {len(pending)}")
        print(f"📈 Total Requests: {total_requests}")
        print(f"✅ Completed Responses: {total_responses}")
        print(
            f"📊 Response Rate: {round(total_responses / max(total_requests, 1) * 100, 1)}%"
        )
        print(f"🕒 System Time: {datetime.now().isoformat()}")
        print("=" * 50)

    def view_recent_responses(self):
        """Display recent expert responses"""
        with expert_system.lock:
            responses = list(expert_system.responses.values())

        if not responses:
            print("\n📭 No responses submitted yet!")
            return

        # Sort by timestamp (most recent first)
        responses.sort(key=lambda x: x["timestamp"], reverse=True)
        recent = responses[:5]  # Show last 5 responses

        print(f"\n📬 RECENT EXPERT RESPONSES ({len(recent)} of {len(responses)}):")
        print("=" * 80)

        for i, resp in enumerate(recent, 1):
            req = resp["request"]
            print(f"\n[{i}] REQUEST ID: {req['id']}")
            print(
                f"❓ Question: {req['question'][:100]}{'...' if len(req['question']) > 100 else ''}"
            )
            print(
                f"✅ Response: {resp['response'][:150]}{'...' if len(resp['response']) > 150 else ''}"
            )
            print(f"👨‍⚕️ Expert: {resp['expert']}")
            print(f"📅 Responded: {resp['timestamp']}")
            print("-" * 50)

    def auto_refresh_loop(self):
        """Auto-refresh pending requests every 30 seconds"""
        print("\n🔄 Auto-refresh mode (Ctrl+C to stop)")
        print("=" * 50)

        try:
            while self.running:
                print(
                    f"\n🕒 {datetime.now().strftime('%H:%M:%S')} - Checking for new requests..."
                )

                pending = expert_system.get_pending_requests()
                if pending:
                    print(f"📋 {len(pending)} pending request(s) found:")
                    for req in pending:
                        age_seconds = (
                            datetime.now() - datetime.fromisoformat(req["timestamp"])
                        ).total_seconds()
                        print(
                            f"  • {req['id']}: {req['question'][:60]}{'...' if len(req['question']) > 60 else ''} ({round(age_seconds / 60, 1)} min old)"
                        )
                else:
                    print("✅ No pending requests")

                print("   (Press Ctrl+C to return to menu)")
                time.sleep(30)

        except KeyboardInterrupt:
            print("\n🔄 Auto-refresh stopped")

    def run(self):
        """Main interface loop"""
        self.display_banner()

        try:
            while self.running:
                self.display_menu()
                choice = input("Select option: ").strip()

                if choice == "1":
                    self.view_pending_requests()
                elif choice == "2":
                    self.respond_to_request()
                elif choice == "3":
                    self.view_system_status()
                elif choice == "4":
                    self.view_recent_responses()
                elif choice.lower() in ["refresh", "r", "🔄"]:
                    self.auto_refresh_loop()
                elif choice.lower() in ["quit", "q", "exit", "❌"]:
                    self.running = False
                    print("\n👋 Expert interface closed. Have a great day!")
                    break
                else:
                    print("❌ Invalid option! Please try again.")

                if self.running:
                    input("\nPress Enter to continue...")

        except KeyboardInterrupt:
            print("\n\n👋 Expert interface closed. Have a great day!")


# =============================================================================
# 🚀 STARTUP FUNCTIONS
# =============================================================================


def start_http_api_server(port=9877):
    """Start the HTTP API server for expert system communication"""
    if not FLASK_AVAILABLE:
        print("⚠️  Cannot start HTTP API server: Flask not installed")
        return

    api_app = create_http_api_server()
    if api_app is None:
        print("⚠️  Failed to create HTTP API server")
        return

    import threading

    def run_api_server():
        print(f"🌐 Starting HTTP API server on port {port}")
        print(f"📡 API endpoints available at http://0.0.0.0:{port}/api/")
        try:
            api_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"❌ HTTP API server failed: {e}")

    # Start API server in background thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()

    # Give the server a moment to start
    import time

    time.sleep(1)

    return api_thread


def start_web_server():
    """Start the Flask web server for expert interface"""
    if not FLASK_AVAILABLE:
        print("❌ Cannot start web interface: Flask not installed")
        print("   Install with: pip install flask")
        return

    app = create_web_app()
    if app:
        print("🌐 Starting web interface on http://localhost:8090")
        app.run(host="0.0.0.0", port=8090, debug=False, use_reloader=False)


def run_expert_interface():
    """Run the terminal-based expert interface"""
    interface = ExpertInterface()
    interface.run()


def open_web_interface():
    """Open web interface in default browser"""
    if not FLASK_AVAILABLE:
        print("⚠️  Web interface not available (Flask not installed)")
        return

    def open_browser():
        try:
            webbrowser.open("http://localhost:8090")
        except Exception as e:
            print(f"Could not open browser automatically: {str(e)}")
            print("Please manually open: http://localhost:8090")

    # Delay browser opening to allow server to start
    Timer(2.0, open_browser).start()


def start_monitoring_thread():
    """Start background monitoring thread for system health"""

    def monitor():
        while True:
            try:
                # Basic system monitoring
                pending_count = len(expert_system.get_pending_requests())
                if pending_count > 0:
                    print(
                        f"🔔 {pending_count} pending expert request(s) - experts needed!"
                    )
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(60)

    monitor_thread = threading.Thread(target=monitor, daemon=True)
    monitor_thread.start()


# =============================================================================
# 🎯 MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for console script"""
    parser = argparse.ArgumentParser(
        description="Human Expert Tools - MCP Registration System"
    )
    parser.add_argument(
        "--interface-only",
        action="store_true",
        help="Start only the expert terminal interface",
    )
    parser.add_argument(
        "--web-only", action="store_true", help="Start only the web interface"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not automatically open browser for web interface",
    )
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Start the MCP server with registered tools",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Specify the MCP server port (default: random available port)",
    )
    parser.add_argument(
        "--mcp-host",
        type=str,
        default="localhost",
        help="MCP server host for web interface to connect to (default: localhost)",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=9876,
        help="MCP server port for web interface to connect to (default: 9876)",
    )
    args = parser.parse_args()

    # Set environment variables for API server connection (used by web interface)
    import os

    if args.mcp_host != "localhost":
        os.environ["EXPERT_FEEDBACK_API_HOST"] = args.mcp_host
    # Map MCP port to API port for backward compatibility
    api_port = args.mcp_port + 1 if args.mcp_port != 9876 else 9877
    os.environ["EXPERT_FEEDBACK_API_PORT"] = str(api_port)

    if args.interface_only:
        # Run only the terminal expert interface
        print("💻 Starting Expert Terminal Interface...")
        run_expert_interface()
    elif args.web_only:
        # Run only the web interface
        if not FLASK_AVAILABLE:
            print("❌ Cannot start web interface: Flask not installed")
            print("   Install with: pip install flask")
            sys.exit(1)

        print("🌐 Starting Human Expert Web Interface...")
        print(f"🔗 Will connect to API server at: {args.mcp_host}:{api_port}")
        print("💡 To connect to a different API server, use:")
        print(
            "   tooluniverse-expert-feedback --web-only --mcp-host <api-host> --mcp-port <mcp-port>"
        )
        print("   (API port will be automatically calculated as MCP port + 1)")
        if not args.no_browser:
            open_web_interface()
        start_web_server()
    elif args.start_server:
        # Determine the port to use
        port = args.port if args.port is not None else 9876

        # Tools are already registered via decorators at module import time
        print("🚀 Starting MCP Server with Expert Tools...")
        print(f"🔌 MCP Server Port: {port}")
        print("📋 Registered tools:")
        print("   - consult_human_expert: Submit questions to human experts")
        print("   - get_expert_response: Check for expert responses")
        print("   - list_pending_expert_requests: View pending requests (for experts)")
        print("   - submit_expert_response: Submit expert responses (for experts)")
        print("   - get_expert_status: Get system status")

        print("\n📡 Starting HTTP API Server...")
        api_port = 9877  # Default API port
        try:
            start_http_api_server(api_port)
            print(f"✅ HTTP API server started on port {api_port}")
            print(f"🌐 API endpoints: http://localhost:{api_port}/api/")
        except Exception as e:
            print(f"⚠️  HTTP API server failed to start: {e}")

        print("\n🔄 Starting background monitoring...")
        start_monitoring_thread()

        print("\n🎯 Expert Interface Options:")
        print(
            f"   🌐 Web Interface: tooluniverse-expert-feedback --web-only --mcp-host localhost --mcp-port {api_port}"
        )
        print("   💻 Terminal Interface: tooluniverse-expert-feedback --interface-only")
        print("\n💡 For remote experts, use:")
        print("   export EXPERT_FEEDBACK_API_HOST=<this-server-ip>")
        print(f"   export EXPERT_FEEDBACK_API_PORT={api_port}")

        # Start the MCP server using the standard method
        print(f"\n✅ Starting MCP server on port {port}...")
        start_mcp_server()
    else:
        # Default: show usage information
        print("🧑‍⚕️ Human Expert MCP Tools - Console Script")
        print("=" * 50)
        print("This tool provides human expert consultation through MCP protocol.")
        print()
        print("Usage options:")
        print("  --start-server      Start MCP server with expert tools")
        print("  --port PORT         Specify MCP server port (default: 9876)")
        print("  --interface-only    Start expert terminal interface")
        print("  --web-only          Start expert web interface")
        print("  --no-browser        Don't auto-open browser (with --web-only)")
        print()
        print("Examples:")
        print("  tooluniverse-expert-feedback --start-server")
        print("  tooluniverse-expert-feedback --start-server --port 8000")
        print("  tooluniverse-expert-feedback --web-only")
        print()
        print("The tools are automatically registered and available when imported")
        print("by ToolUniverse or when the MCP server is started.")


if __name__ == "__main__":
    main()
