from langchain_core.messages import RemoveMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode

from app.conversation_service.tenant_workflow import (
    get_tenant_agent_chain,
    get_property_matching_chain,
    get_viewing_feedback_analysis_chain,
    get_rental_conversation_summary_chain,
)
from app.conversation_service.tenant_workflow import TenantState
from app.conversation_service import tools
from app.config import config

retriever_node = ToolNode(tools)


async def tenant_agent_node(state: TenantState, config: RunnableConfig):
    """Handle tenant agent conversations"""
    summary = state.get("summary", "")
    tenant_chain = get_tenant_agent_chain()

    response = await tenant_chain.ainvoke(
        {
            "messages": state["messages"],
            "tenant_id": state.get("tenant_id", ""),
            "tenant_name": state.get("tenant_name", ""),
            "email": state.get("email", ""),
            "phone": state.get("phone", ""),
            "annual_income": state.get("annual_income", 0),
            "has_guarantor": state.get("has_guarantor", False),
            "max_budget": state.get("max_budget", 0),
            "min_bedrooms": state.get("min_bedrooms", 1),
            "max_bedrooms": state.get("max_bedrooms", 3),
            "preferred_locations": state.get("preferred_locations", []),
            "is_student": state.get("is_student", False),
            "has_pets": state.get("has_pets", False),
            "is_smoker": state.get("is_smoker", False),
            "num_occupants": state.get("num_occupants", 1),
            "conversation_context": state.get("conversation_context", ""),
            "search_criteria": state.get("search_criteria", {}),
            "viewed_properties": state.get("viewed_properties", []),
            "interested_properties": state.get("interested_properties", []),
            "summary": summary,
        },
        config,
    )
    
    return {"messages": response}


async def property_matching_node(state: TenantState, config: RunnableConfig):
    """Handle property matching analysis for tenant"""
    matching_chain = get_property_matching_chain()

    response = await matching_chain.ainvoke(
        {
            "max_budget": state.get("max_budget", 0),
            "min_bedrooms": state.get("min_bedrooms", 1),
            "max_bedrooms": state.get("max_bedrooms", 3),
            "preferred_locations": state.get("preferred_locations", []),
            "is_student": state.get("is_student", False),
            "has_pets": state.get("has_pets", False),
            "is_smoker": state.get("is_smoker", False),
            "num_occupants": state.get("num_occupants", 1),
            "has_guarantor": state.get("has_guarantor", False),
            "properties": state.get("properties", []),  # Available properties
        },
        config,
    )
    
    return {"messages": response}


async def viewing_feedback_analysis_node(state: TenantState, config: RunnableConfig):
    """Handle property viewing feedback analysis"""
    feedback_chain = get_viewing_feedback_analysis_chain()

    # Get the latest message which should contain viewing feedback
    latest_message = state["messages"][-1] if state["messages"] else None
    
    response = await feedback_chain.ainvoke(
        {
            "property_address": "",  # To be extracted from context
            "viewing_date": "",      # To be extracted from context
            "attendees": [state.get("tenant_name", "")],
            "tenant_feedback": latest_message.content if latest_message else "",
            "interests": "",         # To be extracted from feedback
            "concerns": "",          # To be extracted from feedback
            "questions": "",         # To be extracted from feedback
        },
        config,
    )
    
    return {"messages": response}


async def summarize_conversation_node(state: TenantState):
    """Summarize tenant conversation and remove old messages"""
    summary = state.get("summary", "")
    summary_chain = get_rental_conversation_summary_chain(summary)

    response = await summary_chain.ainvoke(
        {
            "messages": state["messages"],
            "conversation_context": state.get("conversation_context", ""),
            "summary": summary,
        }
    )

    # Get the number of messages to keep after summary from config
    messages_after_summary = 5
    if config.agents and config.agents.total_messages_after_summary:
        messages_after_summary = config.agents.total_messages_after_summary

    delete_messages = [
        RemoveMessage(id=m.id)
        for m in state["messages"][: -messages_after_summary]
    ]
    return {"summary": response.content, "messages": delete_messages}


async def connector_node(state: TenantState):
    """Connector node for tenant workflow routing"""
    return {}
