import sentencepiece as spm 
sp = spm.SentencePieceProcessor() 
result = sp.Load(r'e:\SV\Ki6\PBL5\PBL5_DoAnNhaThongMinh\AI_NLP\NLU\tokenizer\vi_smarthome_bpe.model') 
print('OK:', sp.get_piece_size()) 
