from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-32B") 

# Add your new special token
new_token = "[YOUR_SPECIAL_TOKEN]" 
tokenizer.add_special_tokens([new_token]) 

# Resize the model to accommodate the new token (if needed)
model = AutoModelForSequenceClassification.from_pretrained("/shared/data/models/32b_resized")
model.resize_token_embeddings(len(tokenizer)) 