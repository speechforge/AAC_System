import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '../indictts/inference')))
try:
    from src.inference import TextToSpeechEngine
    print('TextToSpeechEngine imported successfully')
except Exception as e:
    import traceback
    traceback.print_exc()
