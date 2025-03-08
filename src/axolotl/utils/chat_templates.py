"""
This module provides functionality for selecting chat templates based on user choices.
These templates are used for formatting messages in a conversation.
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from transformers import PreTrainedTokenizerBase

LOG = logging.getLogger("axolotl.utils.chat_templates")

_JINJA_TEMPALTE_CHOICE = "jinja"
_DEFAULT_TEMPLATE_CHOICE = "tokenizer_default"
_DEFAULT_FALLBACK_CHATML_TEMPLATE_CHOICE_PREFIX = "tokenizer_default_fallback_"

_CHAT_TEMPLATES = {
    "alpaca": "{{ bos_token }}{% for message in messages %}{% if message['role'] == 'system' and loop.first %}{{ message['content'] }}{% elif message['role'] == 'user' %}{{ '### Instruction:\n' + message['content'] }}{% elif message['role'] == 'assistant' %}{{ '### Response:\n' + message['content'] + eos_token }}{% endif %}{% if not loop.last %}{{ '\n\n' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '\n\n### Response:\n' }}{% endif %}",
    "mistral_v1": "{{ bos_token }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}{{ ' [INST] ' + message['content'] + ' [/INST]' }}{% elif message['role'] == 'assistant' %}{{ ' ' + message['content'] + eos_token}}{% else %}{{ raise_exception('Only user and assistant roles are supported!') }}{% endif %}{% endfor %}",  # Mistral 7B V1, Mistral 7B V2, Mixtral 8x7B V1...
    "mistral_v2v3": "{{ bos_token }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}{{ '[INST] ' + message['content'] + '[/INST]' }}{% elif message['role'] == 'assistant' %}{{ ' ' + message['content'] + eos_token}}{% else %}{{ raise_exception('Only user and assistant roles are supported!') }}{% endif %}{% endfor %}",  # V3: Mistral 7B V3, Small, Large...
    "mistral_v3_tekken": "{{ bos_token }}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if message['role'] == 'user' %}{{ '[INST]' + message['content'] + '[/INST]' }}{% elif message['role'] == 'assistant' %}{{ message['content'] + eos_token}}{% else %}{{ raise_exception('Only user and assistant roles are supported!') }}{% endif %}{% endfor %}",  # V3-Tekken: Nemo, Pixtral...
    "chatml": "{% if messages|length == 0 or messages[0]['role'] != 'system' %}{{ '<|im_start|>system<|im_sep|>You are a helpful assistant<|im_end|>' }}{% endif %}{% for message in messages %}{{ '<|im_start|>' + message['role'] + '<|im_sep|>' + message['content'] }}{% if message['role'] != 'assistant' %}{{ '<|im_end|>' }}{% else %}{{ eos_token }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|im_start|>assistant<|im_sep|>' }}{% endif %}",
    "gemma": "{{ bos_token }}{% if messages[0]['role'] == 'system' %}{{ raise_exception('System role not supported') }}{% endif %}{% for message in messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% if (message['role'] == 'assistant') %}{% set role = 'model' %}{% else %}{% set role = message['role'] %}{% endif %}{{ '<start_of_turn>' + role + '\n' + message['content'] | trim + '<end_of_turn>\n' }}{% endfor %}{% if add_generation_prompt %}{{'<start_of_turn>model\n'}}{% endif %}",
    "cohere": "{{ bos_token }}{% if messages[0]['role'] == 'system' %}{% set loop_messages = messages[1:] %}{% set system_message = messages[0]['content'] %}{% elif false == true %}{% set loop_messages = messages %}{% set system_message = 'You are Command-R, a brilliant, sophisticated, AI-assistant trained to assist human users by providing thorough responses. You are trained by Cohere.' %}{% else %}{% set loop_messages = messages %}{% set system_message = false %}{% endif %}{% if system_message != false %}{{ '<|START_OF_TURN_TOKEN|><|SYSTEM_TOKEN|>' + system_message + '<|END_OF_TURN_TOKEN|>' }}{% endif %}{% for message in loop_messages %}{% if (message['role'] == 'user') != (loop.index0 % 2 == 0) %}{{ raise_exception('Conversation roles must alternate user/assistant/user/assistant/...') }}{% endif %}{% set content = message['content'] %}{% if message['role'] == 'user' %}{{ '<|START_OF_TURN_TOKEN|><|USER_TOKEN|>' + content.strip() + '<|END_OF_TURN_TOKEN|>' }}{% elif message['role'] == 'assistant' %}{{ '<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>'  + content.strip() + '<|END_OF_TURN_TOKEN|>' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|START_OF_TURN_TOKEN|><|CHATBOT_TOKEN|>' }}{% endif %}",
    "llama3": "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{% set loop_messages = messages %}{% for message in loop_messages %}{% set content = '<|start_header_id|>' + message['role'] + '<|end_header_id|>\n\n'+ message['content'] | trim + '<|eot_id|>' %}{% if loop.index0 == 0 %}{% set content = bos_token + content %}{% endif %}{{ content }}{% endfor %}{% if add_generation_prompt %}{{ '<|start_header_id|>assistant<|end_header_id|>\n\n' }}{% endif %}",
    "llama3_2_vision": '{{- bos_token }}\n{%- if custom_tools is defined %}\n    {%- set tools = custom_tools %}\n{%- endif %}\n{%- if not tools_in_user_message is defined %}\n    {%- set tools_in_user_message = true %}\n{%- endif %}\n{%- if not date_string is defined %}\n    {%- if strftime_now is defined %}\n        {%- set date_string = strftime_now("%d %b %Y") %}\n    {%- else %}\n        {%- set date_string = "26 Jul 2024" %}\n    {%- endif %}\n{%- endif %}\n{%- if not tools is defined %}\n    {%- set tools = none %}\n{%- endif %}\n\n{#- This block extracts the system message, so we can slot it into the right place. #}\n{%- if messages[0][\'role\'] == \'system\' %}\n    {%- set system_message = messages[0][\'content\']|trim %}\n    {%- set messages = messages[1:] %}\n{%- else %}\n    {%- set system_message = "" %}\n{%- endif %}\n\n{#- Find out if there are any images #}\n{% set image_ns = namespace(has_images=false) %}      \n{%- for message in messages %}\n    {%- for content in message[\'content\'] %}\n        {%- if content[\'type\'] == \'image\' %}\n            {%- set image_ns.has_images = true %}\n        {%- endif %}\n    {%- endfor %}\n{%- endfor %}\n\n{#- Error out if there are images and system message #}\n{%- if image_ns.has_images and not system_message == "" %}\n    {{- raise_exception("Prompting with images is incompatible with system messages.") }}\n{%- endif %}\n\n{#- System message if there are no images #}\n{%- if not image_ns.has_images %}\n    {{- "<|start_header_id|>system<|end_header_id|>\\n\\n" }}\n    {%- if tools is not none %}\n        {{- "Environment: ipython\\n" }}\n    {%- endif %}\n    {{- "Cutting Knowledge Date: December 2023\\n" }}\n    {{- "Today Date: " + date_string + "\\n\\n" }}\n    {%- if tools is not none and not tools_in_user_message %}\n        {{- "You have access to the following functions. To call a function, please respond with JSON for a function call." }}\n        {{- \'Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\' }}\n        {{- "Do not use variables.\\n\\n" }}\n        {%- for t in tools %}\n            {{- t | tojson(indent=4) }}\n            {{- "\\n\\n" }}\n        {%- endfor %}\n    {%- endif %}\n    {{- system_message }}\n    {{- "<|eot_id|>" }}\n{%- endif %}\n\n{#- Custom tools are passed in a user message with some extra guidance #}\n{%- if tools_in_user_message and not tools is none %}\n    {#- Extract the first user message so we can plug it in here #}\n    {%- if messages | length != 0 %}\n        {%- set first_user_message = messages[0][\'content\']|trim %}\n        {%- set messages = messages[1:] %}\n    {%- else %}\n        {{- raise_exception("Cannot put tools in the first user message when there\'s no first user message!") }}\n{%- endif %}\n    {{- \'<|start_header_id|>user<|end_header_id|>\\n\\n\' -}}\n    {{- "Given the following functions, please respond with a JSON for a function call " }}\n    {{- "with its proper arguments that best answers the given prompt.\\n\\n" }}\n    {{- \'Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}.\' }}\n    {{- "Do not use variables.\\n\\n" }}\n    {%- for t in tools %}\n        {{- t | tojson(indent=4) }}\n        {{- "\\n\\n" }}\n    {%- endfor %}\n    {{- first_user_message + "<|eot_id|>"}}\n{%- endif %}\n\n{%- for message in messages %}\n    {%- if not (message.role == \'ipython\' or message.role == \'tool\' or \'tool_calls\' in message) %}\n    {{- \'<|start_header_id|>\' + message[\'role\'] + \'<|end_header_id|>\\n\\n\' }}\n        {%- if message[\'content\'] is string %}\n            {{- message[\'content\'] }}\n        {%- else %}\n            {%- for content in message[\'content\'] %}\n                {%- if content[\'type\'] == \'image\' %}\n                    {{- \'<|image|>\' }}\n                {%- elif content[\'type\'] == \'text\' %}\n                    {{- content[\'text\'] }}\n                {%- endif %}\n            {%- endfor %}\n        {%- endif %}\n        {{- \'<|eot_id|>\' }}\n    {%- elif \'tool_calls\' in message %}\n        {%- if not message.tool_calls|length == 1 %}\n            {{- raise_exception("This model only supports single tool-calls at once!") }}\n        {%- endif %}\n        {%- set tool_call = message.tool_calls[0].function %}\n        {{- \'<|start_header_id|>assistant<|end_header_id|>\\n\\n\' -}}\n        {{- \'{"name": "\' + tool_call.name + \'", \' }}\n        {{- \'"parameters": \' }}\n        {{- tool_call.arguments | tojson }}\n        {{- "}" }}\n        {{- "<|eot_id|>" }}\n    {%- elif message.role == "tool" or message.role == "ipython" %}\n        {{- "<|start_header_id|>ipython<|end_header_id|>\\n\\n" }}\n        {%- if message.content is mapping or message.content is iterable %}\n            {{- message.content | tojson }}\n        {%- else %}\n            {{- message.content }}\n        {%- endif %}\n        {{- "<|eot_id|>" }}\n    {%- endif %}\n{%- endfor %}\n{%- if add_generation_prompt %}\n    {{- \'<|start_header_id|>assistant<|end_header_id|>\\n\\n\' }}\n{%- endif %}\n',
    "phi_3": "{{ bos_token }}{% for message in messages %}{% if (message['role'] == 'system') %}{{'<|system|>' + '\n' + message['content'] + '<|end|>' + '\n'}}{% elif (message['role'] == 'user') %}{{'<|user|>' + '\n' + message['content'] + '<|end|>' + '\n' + '<|assistant|>' + '\n'}}{% elif message['role'] == 'assistant' %}{{message['content'] + '<|end|>' + '\n'}}{% endif %}{% endfor %}",
    "phi_35": "{% for message in messages %}{% if message['role'] == 'system' and message['content'] %}{{'<|system|>\n' + message['content'] + '<|end|>\n'}}{% elif message['role'] == 'user' %}{{'<|user|>\n' + message['content'] + '<|end|>\n'}}{% elif message['role'] == 'assistant' %}{{'<|assistant|>\n' + message['content'] + '<|end|>\n'}}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|assistant|>\n' }}{% endif %}",
    "deepseek_v2": "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{{ bos_token }}{% for message in messages %}{% if message['role'] == 'user' %}{{ '<｜User｜>' + message['content'] }}{% elif message['role'] == 'assistant' %}{{ '<｜Assistant｜>' + message['content'] + eos_token }}{% elif message['role'] == 'system' %}{{ message['content'] + '\n\n' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<｜Assistant｜>' }}{% endif %}",
    "deepseek_v3": "{% if not add_generation_prompt is defined %}{% set add_generation_prompt = false %}{% endif %}{% set ns = namespace(is_first=false, is_tool=false, is_output_first=true, system_prompt='', is_first_sp=true) %}{%- for message in messages %}{%- if message['role'] == 'system' %}{%- if ns.is_first_sp %}{% set ns.system_prompt = ns.system_prompt + message['content'] %}{% set ns.is_first_sp = false %}{%- else %}{% set ns.system_prompt = ns.system_prompt + '\\n\\n' + message['content'] %}{%- endif %}{%- endif %}{%- endfor %}{{ bos_token }}{{ ns.system_prompt }}{%- for message in messages %}{%- if message['role'] == 'user' %}{%- set ns.is_tool = false -%}{{'<｜User｜>' + message['content']}}{%- endif %}{%- if message['role'] == 'assistant' and 'tool_calls' in message %}{%- set ns.is_tool = false -%}{%- for tool in message['tool_calls'] %}{%- if not ns.is_first %}{%- if message['content'] is none %}{{'<｜Assistant｜><｜tool▁calls▁begin｜><｜tool▁call▁begin｜>' + tool['type'] + '<｜tool▁sep｜>' + tool['function']['name'] + '\\n' + '```json' + '\\n' + tool['function']['arguments'] + '\\n' + '```' + '<｜tool▁call▁end｜>'}}{%- else %}{{'<｜Assistant｜>' + message['content'] + '<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>' + tool['type'] + '<｜tool▁sep｜>' + tool['function']['name'] + '\\n' + '```json' + '\\n' + tool['function']['arguments'] + '\\n' + '```' + '<｜tool▁call▁end｜>'}}{%- endif %}{%- set ns.is_first = true -%}{%- else %}{{'\\n' + '<｜tool▁call▁begin｜>' + tool['type'] + '<｜tool▁sep｜>' + tool['function']['name'] + '\\n' + '```json' + '\\n' + tool['function']['arguments'] + '\\n' + '```' + '<｜tool▁call▁end｜>'}}{%- endif %}{%- endfor %}{{'<｜tool▁calls▁end｜><｜end▁of▁sentence｜>'}}{%- endif %}{%- if message['role'] == 'assistant' and 'tool_calls' not in message %}{%- if ns.is_tool %}{{'<｜tool▁outputs▁end｜>' + message['content'] + '<｜end▁of▁sentence｜>'}}{%- set ns.is_tool = false -%}{%- else %}{% set content = message['content'] %}{% if '</think>' in content %}{% set content = content.split('</think>')[-1] %}{% endif %}{{'<｜Assistant｜>' + content + '<｜end▁of▁sentence｜>'}}{%- endif %}{%- endif %}{%- if message['role'] == 'tool' %}{%- set ns.is_tool = true -%}{%- if ns.is_output_first %}{{'<｜tool▁outputs▁begin｜><｜tool▁output▁begin｜>' + message['content'] + '<｜tool▁output▁end｜>'}}{%- set ns.is_output_first = false %}{%- else %}{{'<｜tool▁output▁begin｜>' + message['content'] + '<｜tool▁output▁end｜>'}}{%- endif %}{%- endif %}{%- endfor -%}{% if ns.is_tool %}{{'<｜tool▁outputs▁end｜>'}}{% endif %}{% if add_generation_prompt and not ns.is_tool %}{{'<｜Assistant｜>'}}{% endif %}",
    "jamba": '{# Variables #}\n{% set ns = namespace(message_count=0, is_last_checked_defined=False) %}\n{##}\n{% set bom_str = bom_str or "<|bom|>" %}\n{% set eom_str = eom_str or "<|eom|>" %}\n{% set default_system_message = "" %}\n{##}\n{% set documents_prefix = "<documents>" %}\n{% set documents_suffix = "</documents>" %}\n{% set tool_definitions_prefix = "<tool_definitions>" %}\n{% set tool_definitions_suffix = "</tool_definitions>" %}\n{% set active_modes_prefix = "<active_output_modes>" %}\n{% set active_modes_suffix = "</active_output_modes>" %}\n{##}\n{% set tool_calls_prefix = "<tool_calls>" %}\n{% set tool_calls_suffix = "</tool_calls>" %}\n{% set citations_prefix = "<citations>" %}\n{% set citations_suffix = "</citations>" %}\n{##}\n{% if add_generation_prompt is not defined %}\n  {% set add_generation_prompt = True %}\n{% endif %}\n{% set role_to_predict = role_to_predict or "assistant" %}\n{% if messages|length > 0 and messages[0].role == "system" %}\n  {% set system_message = messages[0].content %}\n  {% set loop_messages = messages[1:] %}\n{% else %}\n  {% set system_message = default_system_message %}\n  {% set loop_messages = messages %}\n{% endif %}\n{##}\n{##}\n{# Macros #}\n{% macro handle_tool_definitions(tools) %}\n  {{- tool_definitions_prefix -}}\n  {{- "\\n# Tools" -}}\n  {{- "\\n\\n## Functions" -}}\n  {% for tool in tools %}\n    {% set _ = is_param_set(tool, field="type") %}\n    {% set is_tool_type_set = ns.is_last_checked_defined %}\n    {% if is_tool_type_set %}\n      {% if tool.type == "function" %}\n        {% set tool = tool.function %}\n      {% else %}\n        {{ raise_exception("Currently, the only supported tool type is `function`") }}\n      {% endif %}\n    {% endif %}\n    {{- "\\n\\n" + (tool|tojson(indent=2)) -}}\n  {% endfor %}\n  {{- "\\n" + tool_definitions_suffix -}}\n{% endmacro %}\n{##}\n{% macro handle_first_system_message(system_message, tools) %}\n  {{- bom_str + handle_role("system") -}}\n  {% set _ = is_param_set(system_message) %}\n  {% set is_system_message_set = ns.is_last_checked_defined %}\n  {% if is_system_message_set %}\n    {{- system_message -}}\n  {% endif %}\n  {% set _ = is_param_set(tools, is_list=True) %}\n  {% set is_tools_set = ns.is_last_checked_defined %}\n  {% if is_tools_set %}\n    {% if system_message %}\n      {{- "\\n\\n" -}}\n    {% endif %}\n    {{- handle_tool_definitions(tools) -}}\n  {% endif %}\n  {% set ns.message_count = ns.message_count + 1 %}\n{% endmacro %}\n{##}\n{% macro handle_tool_calls(tool_calls) %}\n  {{- tool_calls_prefix + "[\\n" -}}\n  {% for tool_call in tool_calls %}\n    {% set _ = is_param_set(tool_call, field="function") %}\n    {% set is_tool_call_function_set = ns.is_last_checked_defined %}\n    {% if is_tool_call_function_set %}\n      {%- set tool_call = tool_call.function %}\n    {%- endif %}\n    {% set arguments = tool_call.arguments %}\n    {% if arguments is not string %}\n      {%- set arguments = arguments|tojson -%}\n    {%- endif %}\n    {{ "{\\"name\\": \\"" + tool_call.name + "\\", \\"arguments\\": " + arguments + "}" -}}\n    {% if not loop.last %}\n      {{- "," }}\n    {% endif %}\n  {% endfor %}\n  {{- "\\n]" + tool_calls_suffix -}}\n{% endmacro %}\n{##}\n{% macro handle_documents(documents) %}\n  {{- documents_prefix -}}\n  {{- "\\n# Documents" -}}\n  {{- "\\n\\nYou can use the following documents for reference:" -}}\n  {% for doc in documents %}\n    {{- "\\n\\n## Document ID: " + loop.index0|string -}}\n    {% set _ = is_param_set(doc, field="title") %}\n    {% set is_doc_title_set = ns.is_last_checked_defined %}\n    {% if is_doc_title_set %}\n      {{- "\\nTitle: " + doc.title -}}\n    {% endif %}\n    {% for key, value in doc.items() %}\n      {% if key not in ["title", "text"] %}\n        {{- "\\n" + key|title + ": " + value|string -}}\n      {% endif %}\n    {% endfor %}\n    {{- "\\nText: " + doc.text -}}\n  {% endfor %}\n  {{- "\\n" + documents_suffix -}}\n{% endmacro %}\n{##}\n{% macro handle_knobs(knobs) %}\n  {{- active_modes_prefix -}}\n  {{- "\\n# Active Modes" -}}\n  {{ "\\n\\nThe following modes configure the format or style of your responses. You should adhere to all currently" -}}\n  {{ " active modes simultaneously." -}}\n  {% if knobs.citation_mode == "fast" %}\n    {{- "\\n\\n## Citation Mode" -}}\n    {{- "\\n\\nProvide a list of references only for the documents you base your response on. Format your response" -}}\n    {{ " with the original answer followed by a citation section. Use this template:" -}}\n    {{ " `{answer}" + citations_prefix + "DOCUMENT_IDS" + citations_suffix + "`, where DOCUMENT_IDS are the relevant document numbers" -}}\n    {{ " (e.g. [2, 5, 9]), or [] if the answer cannot be supported by the provided documents." -}}\n  {% endif %}\n  {% if knobs.response_format == "json_object" %}\n    {{- "\\n\\n## JSON Mode" -}}\n    {{ "\\n\\nProvide your response in JSON format. Adhere strictly to any schema given by the user." -}}\n    {{ " If an appropriate JSON format exists, use it without modification." -}}\n  {% endif %}\n  {{- "\\n" + active_modes_suffix -}}\n{% endmacro %}\n{##}\n{% macro get_last_user_index(messages) %}\n  {% set ns.last_user_index = 0 %}\n  {% for message in messages %}\n    {% if message.role == \'user\' %}\n      {% set ns.last_user_index = loop.index0 %}\n    {% endif %}\n  {% endfor %}\n  {{- ns.last_user_index -}}\n{% endmacro %}\n{##}\n{% macro handle_last_system_message(documents, knobs, use_documents, use_knobs) %}\n  {{- bom_str + handle_role("system") -}}\n  {% set macros_to_call = [] %}\n  {% set params_for_macros = [] %}\n  {% if use_documents %}\n    {% set macros_to_call = macros_to_call + [handle_documents] %}\n    {% set params_for_macros = params_for_macros + [[documents]] %}\n  {% endif %}\n  {% if use_knobs %}\n    {% set macros_to_call = macros_to_call + [handle_knobs] %}\n    {% set params_for_macros = params_for_macros + [[knobs]] %}\n  {% endif %}\n  {% for i in range(macros_to_call|length) %}\n    {% if i > 0 %}\n      {{- "\\n\\n" -}}\n    {% endif %}\n    {{- macros_to_call[i](*params_for_macros[i]) -}}\n  {% endfor %}\n  {% set ns.message_count = ns.message_count + 1 %}\n{% endmacro %}\n{##}\n{% macro handle_role(role, add_space=True) %}\n  {{- "<|" + role + "|>" -}}\n  {% if add_space %}\n    {{- " " -}}\n  {% endif %}\n{% endmacro %}\n{##}\n{% macro is_param_set(param, field=none, is_list=False) %}\n  {% if field is not none %}\n    {% if field in param %}\n      {% set param = param[field] %}\n    {% else %}\n      {% set param = none %}\n    {% endif %}\n  {% endif %}\n  {% set is_defined = param is defined and param is not none %}\n  {% if is_list %}\n    {% set ns.is_last_checked_defined = is_defined and param|length > 0 %}\n  {% else %}\n    {% set ns.is_last_checked_defined = is_defined %}\n  {% endif %}\n{% endmacro %}\n{##}\n{##}\n{# Template #}\n{{- "<|startoftext|>" -}}\n{% set _ = is_param_set(system_message) %}\n{% set is_system_message_set = ns.is_last_checked_defined %}\n{% set _ = is_param_set(tools, is_list=True) %}\n{% set is_tools_set = ns.is_last_checked_defined %}\n{% set has_system_message = (is_system_message_set or is_tools_set) %}\n{% if has_system_message %}\n  {{- handle_first_system_message(system_message, tools) -}}\n{% endif %}\n{% set last_user_index = get_last_user_index(loop_messages)|int %}\n{% for message in loop_messages %}\n  {% if loop.index0 == last_user_index %}\n    {% set _ = is_param_set(documents, is_list=True) %}\n    {% set use_documents = ns.is_last_checked_defined %}\n    {% set _ = is_param_set(knobs) %}\n    {% set use_knobs = ns.is_last_checked_defined and knobs.is_set %}\n    {% set add_last_system_message = use_documents or use_knobs %}\n    {% if add_last_system_message %}\n      {% if ns.message_count > 0 %}\n        {{- eom_str -}}\n      {% endif %}\n      {{- handle_last_system_message(documents, knobs, use_documents, use_knobs) -}}\n    {% endif %}\n  {% endif %}\n  {% set role = message.role %}\n  {% set _ = is_param_set(message, field="name") %}\n  {% set is_message_name_set = ns.is_last_checked_defined %}\n  {% if is_message_name_set %}\n    {% set message_prefix = handle_role(role) + "(" + message.name + ")" %}\n  {% else %}\n    {% set message_prefix = handle_role(role) %}\n  {% endif %}\n  {% set content = (message.content or "") %}\n  {% if content is not string %}\n    {% set content = content|tojson %}\n  {% endif %}\n  {% if ns.message_count > 0 %}\n    {{- eom_str -}}\n  {% endif %}\n  {{- bom_str + message_prefix + content -}}\n  {% set _ = is_param_set(message, field="tool_calls", is_list=True) %}\n  {% set is_tool_calls_set = ns.is_last_checked_defined %}\n  {% if role == "assistant" and is_tool_calls_set %}\n    {{- handle_tool_calls(message.tool_calls) -}}\n  {% endif %}\n  {% set _ = is_param_set(message, field="citations", is_list=True) %}\n  {% set is_citations_set = ns.is_last_checked_defined %}\n  {% if role == "assistant" and is_citations_set %}\n    {{- citations_prefix + message.citations|map(attribute="document_id")|list|string + citations_suffix -}}\n  {% endif %}\n  {% set ns.message_count = ns.message_count + 1 %}\n{% endfor %}\n{% if add_generation_prompt %}\n  {% if ns.message_count > 0 %}\n    {{- eom_str -}}\n  {% endif %}\n  {{- bom_str + handle_role(role_to_predict, add_space=False) -}}\n  {% set _ = is_param_set(generation_preamble) %}\n  {% set is_generation_preamble_set = ns.is_last_checked_defined %}\n  {% if is_generation_preamble_set and generation_preamble.strip() != "" %}\n    {{- " " + generation_preamble -}}\n  {% endif %}\n  {% set ns.message_count = ns.message_count + 1 %}\n{% else %}\n  {% if ns.message_count > 0 %}\n    {{- eom_str -}}\n  {% endif %}\n{% endif %}\n',
    "qwen_25": "{%- if tools %}\n    {{- '<|im_start|>system\\n' }}\n    {%- if messages[0]['role'] == 'system' %}\n        {{- messages[0]['content'] }}\n    {%- else %}\n        {{- 'You are a helpful assistant.' }}\n    {%- endif %}\n    {{- \" Your knowledge cut-off date is January 25, 2025, and today's current date is February 17, 2025.\\n\\n# Functions\\n\\nYou have access to function signatures provided within <functions></functions>. You may call one or more of these functions to assist the user.\\n\\n<functions>\" }}\n    {%- for tool in tools %}\n        {{- \"\\n\" }}\n        {{- tool | tojson }}\n    {%- endfor %}\n    {{- '</functions>\\n\\nFor each function call, return a json object with function name and arguments within <function_calls></function_calls> XML tags:\\n<function_calls>\\n<function name=\"<function-name>\">{<args-json-object>}</function>\\n<function name=\"<function-name>\">{<args-json-object>}</function>\\n</function_calls>' }}\n{%- else %}\n    {%- if messages[0]['role'] == 'system' %}\n        {{- '<|im_start|>system\\n' + messages[0]['content'] + '<|im_end|>\\n' }}\n    {%- else %}\n        {{- '<|im_start|>system\\nYou are a helpful assistant.<|im_end|>\\n' }}\n    {%- endif %}\n{%- endif %}\n{%- for message in messages %}\n    {%- if (message.role == \"user\") or (message.role == \"system\" and not loop.first) or (message.role == \"assistant\" and not message.tool_calls) %}\n        {{- '<|im_start|>' + message.role + '\\n' + message.content + '<|im_end|>' + '\\n' }}\n    {%- elif message.role == \"assistant\" %}\n        {{- '<|im_start|>' + message.role }}\n        {%- if message.content %}\n            {{- '\\n' + message.content }}\n        {%- endif %}\n        {%- for tool_call in message.tool_calls %}\n            {%- if tool_call.function is defined %}\n                {%- set tool_call = tool_call.function %}\n            {%- endif %}\n            {{- '\\n<function_calls>\\n<function name=\"' }}            {{- tool_call.name }}\n            {{- '\">' }}            {{- tool_call.arguments | tojson }}\n            {{- '}\\n</function_calls>' }}\n        {%- endfor %}\n        {{- '<|im_end|>\\n' }}\n    {%- elif message.role == \"tool\" %}\n        {%- if (loop.index0 == 0) or (messages[loop.index0 - 1].role != \"tool\") %}\n            {{- '<|im_start|>tool\\n' }}\n        {%- endif %}\n        {{- message.content }}\n        {%- if loop.last or (messages[loop.index0 + 1].role != \"tool\") %}\n            {{- '<|im_end|>\\n' }}\n        {%- endif %}\n    {%- endif %}\n{%- endfor %}\n{%- if add_generation_prompt %}\n    {{- '<|im_start|>assistant\\n' }}\n{%- endif %}\n",
    "exaone": "{% for message in messages %}{% if loop.first and message['role'] != 'system' %}{{ '[|system|][|endofturn|]\n' }}{% endif %}{{ '[|' + message['role'] + '|]' + message['content'] }}{% if message['role'] == 'user' %}{{ '\n' }}{% else %}{{ '[|endofturn|]\n' }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '[|assistant|]' }}{% endif %}",
    "metharme": "{{ bos_token }}{% if messages[0]['role'] == 'system' %}{% set loop_messages = messages[1:] %}{% set system_message = messages[0]['content'] %}{% else %}{% set loop_messages = messages %}{% set system_message = 'Enter RP mode. You shall reply to the user while staying in character. Your responses must be detailed, creative, immersive, and drive the scenario forward.' %}{% endif %}{{ '<|system|>' + system_message }}{% for message in loop_messages %}{% set content = message['content'] %}{% if message['role'] == 'user' %}{{ '<|user|>' + content.strip() }}{% elif message['role'] == 'assistant' %}{{ '<|model|>'  + content.strip() }}{% endif %}{% endfor %}{% if add_generation_prompt %}{{ '<|model|>' }}{% else %}{{ eos_token }}{% endif %}",
}


def get_chat_template(
    user_choice: str,
    jinja_template: Optional[str] = None,
    tokenizer: Optional["PreTrainedTokenizerBase"] = None,
) -> str:
    """
    Finds the correct chat_template based on the user's choice, jinja_template, and tokenizer.

    Args:
        user_choice (str): The user's choice of template.
        jinja_template (Optional[str], optional): The jinja template string. Defaults to None.
        tokenizer (Optional[PreTrainedTokenizerBase], optional): The tokenizer. Defaults to None.

    Returns:
        str: The chosen template string.

    Raises:
        ValueError: If the user_choice is not found in the templates.
    """
    if user_choice == _JINJA_TEMPALTE_CHOICE:
        if not jinja_template:
            raise ValueError(
                f"`jinja_template` cannot be None when `chat_template` choice is {_JINJA_TEMPALTE_CHOICE}"
            )
        return jinja_template

    if user_choice == _DEFAULT_TEMPLATE_CHOICE:
        if not tokenizer:
            raise ValueError(
                f"`tokenizer` cannot be None when chat_template choice is {_DEFAULT_TEMPLATE_CHOICE}"
            )
        if not tokenizer.chat_template:
            raise ValueError(
                f"`chat_template choice is {_DEFAULT_TEMPLATE_CHOICE} but tokenizer's chat_template is null. "
                f"Please add a chat_template in tokenizer config"
            )
        return tokenizer.chat_template  # type: ignore

    if user_choice.startswith(_DEFAULT_FALLBACK_CHATML_TEMPLATE_CHOICE_PREFIX):
        if not tokenizer:
            raise ValueError(
                f"`tokenizer` cannot be None when chat_template choice starts with {_DEFAULT_FALLBACK_CHATML_TEMPLATE_CHOICE_PREFIX}"
            )
        if tokenizer.chat_template:
            return tokenizer.chat_template  # type: ignore

        user_choice = user_choice[
            len(_DEFAULT_FALLBACK_CHATML_TEMPLATE_CHOICE_PREFIX) :
        ]
        LOG.warning(
            f"No chat template found on tokenizer, falling back to {user_choice}. It is recommended to set --train_on_inputs to True for the model to learn this chat template."
        )

    if user_choice in _CHAT_TEMPLATES:
        return _CHAT_TEMPLATES[user_choice]

    raise ValueError(f"Template '{user_choice}' not found.")


def extract_chat_template_args(cfg, ds_cfg: Optional[Dict[str, Any]] = None):
    if ds_cfg and ds_cfg.get("chat_template"):
        chat_template_choice = ds_cfg.get("chat_template") or _DEFAULT_TEMPLATE_CHOICE
        chat_template_jinja = ds_cfg.get("chat_template_jinja")
    else:
        chat_template_choice = cfg.get("chat_template") or _DEFAULT_TEMPLATE_CHOICE
        chat_template_jinja = cfg.get("chat_template_jinja")
    return chat_template_choice, chat_template_jinja


def get_chat_template_from_config(
    cfg,
    ds_cfg: Optional[Dict[str, Any]] = None,
    tokenizer: Optional["PreTrainedTokenizerBase"] = None,
) -> str:
    chat_template_choice, chat_template_jinja = extract_chat_template_args(
        cfg=cfg, ds_cfg=ds_cfg
    )
    return get_chat_template(
        user_choice=chat_template_choice,
        jinja_template=chat_template_jinja,
        tokenizer=tokenizer,
    )


def register_chat_template(template_name: str, chat_template: str):
    """
    Registers chat templates.

    Args:
        template_name (str): The name of the template.
        chat_template (str): The template string.
    """

    if template_name in _CHAT_TEMPLATES:
        raise ValueError(f"Template '{template_name}' already exists.")

    _CHAT_TEMPLATES[template_name] = chat_template
