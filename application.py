#  -*- coding: utf-8 -*- 
import re
import os
import io
import json
import shutil
import base64 
import datetime
import textwrap
import pandas as pd
import google_sheets
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
import ChineseTone
from aip import AipSpeech
from flask import Flask, redirect, url_for, request, render_template, send_from_directory

app = Flask(__name__)

tmp_path = 'tmp/'

# Нүүр хуудас
@app.route('/')
def index():
   return render_template('index.html')
   
# Бүртгэлийн хуудас
@app.route('/login',methods = ['POST', 'GET'])
def login():
	if request.method == 'POST':
		user = request.form['nm']
		return redirect(url_for('success',name = user))
	else:
		user = request.args.get('nm')
		return redirect(url_for('success',name = user))

# Хайчласан зургийг хадгалах, base64-с png болгох
@app.route('/save-crop',methods = ['POST', 'GET'])
def save_crop():

	if request.method == 'POST':

		result = request.get_json(silent=True, force=True)

		img_data = result['imgBase64']
		img_data = img_data[img_data.index('base64,')+len('base64,'):]

		# tmp хавтаст хайчласан зургийг хадгална
		with open(os.path.join(tmp_path, result['word'] + '.png'), "wb") as tmp:
			tmp.write(base64.b64decode(img_data))

		return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/save-audio',methods = ['POST', 'GET'])
def save_audio():

	if request.method == 'POST':

		result = request.get_json(silent=True, force=True)

		filename = result['word']
		if result['this_id']=='audioExampleInput':
			filename += '_example'
		filename += '.mp3'	

		with open(os.path.join(tmp_path, filename), "wb") as tmp:
			tmp.write(base64.b64decode(result['audioBase64']))

		return json.dumps({'success':True}), 200, {'ContentType':'application/json'} 

@app.route('/read-xls',methods = ['POST', 'GET'])
def read_xls():

	if request.method == 'POST':

		result = request.get_json(silent=True, force=True)

		if result['lang'] == 'Chinese':
			SAMPLE_SPREADSHEET_ID = '14mY0zLrTJRPEJTprBen3FOqw1MTjM875qHiL_YHl0TA'
			SAMPLE_RANGE_NAME = '新HSK5000词2!A:O'
			
			df = google_sheets.main(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
			for index, row in df.loc[df['word'] == result['word']].iterrows():
				return json.dumps({'success':True,'row':[row.to_dict()]}), 200, {'ContentType':'application/json'} 
		elif result['lang'] == 'English':
			SAMPLE_SPREADSHEET_ID = '14mY0zLrTJRPEJTprBen3FOqw1MTjM875qHiL_YHl0TA'
			SAMPLE_RANGE_NAME = '新HSK5000词2!A:O'
			
			df = google_sheets.main(SAMPLE_SPREADSHEET_ID, SAMPLE_RANGE_NAME)
			for index, row in df.loc[df['word'] == result['word']].iterrows():
				return json.dumps({'success':True,'row':[row.to_dict()]}), 200, {'ContentType':'application/json'} 

		return json.dumps({'success':False}), 400, {'ContentType':'application/json'} 

# mp4 бичлэгийг үүсгэх
@app.route('/generate',methods = ['POST', 'GET'])
def generate():

	if request.method == 'POST':
		result = request.form
		result = dict(result)

		if result['lang']=='Chinese':
			result = check_result_chinese(result)

		today = datetime.datetime.now().strftime('%Y%m%d') 
		
		# Тухайн үгэнд зориулж шинэ хавтас үүсгэх
		download_path = 'data/%s/%s_%s' % (result['lang'], result['word'], today)
		if not os.path.isdir(download_path):
			os.mkdir(download_path)

		# Тухайн хэлний зориулалтын фонт, хэмжээг авах
		with open('custom_values.json', 'r') as r:
			values = json.loads(r.read())

		# Зураг янзлах
		image_file = generate_image(result, values, download_path)

		# Дуу янзлах
		word_audio_file, example_audio_file = generate_audio(result, download_path)
		if not os.path.isfile(word_audio_file):
			return json.dumps({'success':False, 'error':'Please input the audio file'}), 500, {'ContentType':'application/json'} 

		# Зураг ба дууг нийлүүлж mp4 үүсгэх
		mp4_file = combine(result, download_path, image_file, word_audio_file, example_audio_file)

		with open(os.path.join(download_path, result['word'] + '.txt'), 'w') as f:
			json.dump(result, f, ensure_ascii=False)

		# json.dumps({'success':True, 'mp4':mp4_file}), 200, {'ContentType':'application/json'} 
		return send_from_directory(download_path, mp4_file, as_attachment=True)

def check_result_chinese(result):

	if not result.get('pron', None):
		result['pron'] = ''.join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(result['word']))

	result['pron'] = result['pron'].replace(' ', '') 

	if not result.get('example_pron', None):
		result['example_pron'] = ' '.join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(result['example']))
	
	result['example_pron'] = re.sub(r'[。、！？，《》·：（）]', '', result['example_pron']) 

	return result

def combine(result, download_path, image_file, word_audio_file, example_audio_file):

	output_file = os.path.join(download_path, result['word'] + '.mp4')

	config = {
		'image': image_file,
		'word_audio': word_audio_file,
		'example_audio': example_audio_file,
		'output': output_file,
	}

	if os.path.isfile(output_file):
		os.remove(output_file)

	if os.path.isfile(example_audio_file):
		os.system("""
			ffmpeg -loop 1 \
				   -i {image} \
				   -i "concat:{word_audio}|{example_audio}" \
				   -crf 1 \
				   -t 10 \
				   -s 2048x2048 \
				   -vcodec libx264 \
				   -acodec aac \
				   -pix_fmt yuv420p \
				   {output}""".format(**config))
	else:
		os.system("""
			ffmpeg -loop 1 \
				   -i {image} \
				   -i "concat:{word_audio}|{word_audio}|{word_audio}" \
				   -crf 1 \
				   -t 10 \
				   -s 2048x2048 \
				   -vcodec libx264 \
				   -acodec aac \
				   -pix_fmt yuv420p \
				   {output}""".format(**config))

	return output_file.split('/')[-1]

def generate_audio(result, download_path):
	
	word_audio_file = os.path.join(download_path, result['word'] + '.mp3')
	example_audio_file = os.path.join(download_path, result['word'] + '_example.mp3')
	tmp_word_audio_file = os.path.join(tmp_path, result['word'] + '.mp3')
	tmp_example_audio_file = os.path.join(tmp_path, result['word'] + '_example.mp3')

	if os.path.isfile(tmp_word_audio_file):
		shutil.move(tmp_word_audio_file, word_audio_file)
	if os.path.isfile(tmp_example_audio_file):
		shutil.move(tmp_example_audio_file, example_audio_file)

	if not os.path.isfile(word_audio_file):
		if result['lang']=='Chinese':
			word_audio_file, example_audio_file = generate_audio_chinese(result, download_path)
	
	return word_audio_file, example_audio_file

def generate_audio_chinese(result, download_path):

	client = AipSpeech('17300058', 'G11hfH4f7Gzu8xSKdOUi5nGz', 'GGaF2RZfQGw3GdsMSbnP9oyTG1reMeqz')

	word_audio_file = None
	example_audio_file = None

	# per = random.choice([1,0,3,4,5,106,110,111,103])
	for per in [1,0,3,5,106][:1]: #,4,110,111,103]:
		try:
			word_audio_file = os.path.join(download_path, '%s_%s_baidu.mp3' % (result['word'], per))
			audio_result = client.synthesis(result['word'],'zh',1,{'vol':10,'spd':4,'pit':5,'per':per})
			with open(word_audio_file, 'wb') as f:
				f.write(audio_result)
		except Exception as e:
			raise e

	for per in [1,0,3,5,106][:1]: #,4,110,111,103]:
		try:
			example_audio_file = os.path.join(download_path, '%s_example_%s_baidu.mp3' % (result['word'], per))
			audio_result = client.synthesis(result['example'],'zh',1,{'vol':10,'spd':4,'pit':5,'per':per})
			with open(example_audio_file, 'wb') as f:
				f.write(audio_result)
		except Exception as e:
			raise e

	return word_audio_file, example_audio_file

def generate_image(result, values, download_path):

	tmp_tmp_file = os.path.join(tmp_path, result['word'] + '.png')
	tmp_file = os.path.join(download_path, result['word'] + '_tmp.png')
	image_file = os.path.join(download_path, result['word'] + '.png')

	if os.path.isfile(tmp_tmp_file):
		shutil.move(tmp_tmp_file, tmp_file)

	# Хайчласан зургийг сууриар сонгох
	img = Image.open(tmp_file)
	img = img.resize((2048, 2048))
	
	# Зургийг сүүдэрлэх
	enhancer = ImageEnhance.Brightness(img)
	img = enhancer.enhance(1 - 0.01 * int(result['shadow']))

	# Зураг дээр текст хэлбэрийн агуулгыг нэмэх
	img = add_text(result, values, img)

	# Зураг дээр logo нэмэх
	logo = Image.open('images/logo.png')
	img.paste(logo, (920,1723), mask=logo)

	# Зургийг сануулах
	img.save(image_file)

	return image_file

def add_text(result, values, img):
	
	draw = ImageDraw.Draw(img)
	
	sizes = values[result['lang']]['sizes']
	fonts = values[result['lang']]['fonts']
	space = values[result['lang']]['default_space']
	# spaces = values[result['lang']]['spaces']

	font_word = ImageFont.truetype(fonts['word_font'], int(sizes['word_size']))
	font_pron = ImageFont.truetype(fonts['pron_font'], int(sizes['pron_size']))
	font_mon = ImageFont.truetype(fonts['mon_font'], int(sizes['mon_size'])) 
	font_example_pron = ImageFont.truetype(fonts['example_pron_font'], int(sizes['example_pron_size']))
	font_example = ImageFont.truetype(fonts['example_font'], int(sizes['example_size'])) 
	font_example_mon = ImageFont.truetype(fonts['example_mon_font'], int(sizes['example_mon_size']))

	if result['lang']=='Chinese':
		config = [
				  (0,317,result['word'],font_word),
				  (0,582,"[%s] /%s/" % (result['pos'],result['pron']),font_pron),
				  (0,826,result['mon'],font_mon),
				  (80,1253,result['example_pron'],font_example_pron),
				  (80,1253+int(sizes['example_pron_size'])+space,result['example'],font_example),
				  (80,1253+int(sizes['example_pron_size'])+space+int(sizes['example_size'])+space,result['example_mon'],font_example_mon)]

	elif result['lang']=='English':
		config = [
				  (0,317,result['word'],font_word),
				  (0,582,"[%s]   /%s/" % (result['pos'],result['pron']),font_pron),
				  (0,826,result['mon'],font_mon),
				  (80,1253,result['example'],font_example),
				  (80,1253+int(sizes['example_pron_size'])+space,result['example_mon'],font_example_mon)]

	addition = 0
	for x, y, text, font in config:

		w, h = draw.textsize(text, font=font)

		cnt = 0
		n_letters = 70
		texts = textwrap.wrap(text, width=(n_letters))
		while (w>(2048-80*2) or len(texts)>2) and cnt<500:
			texts = textwrap.wrap(text, width=(n_letters))
			w, h = draw.textsize(texts[0], font=font)
			n_letters -= 1
			cnt += 1

		last_w, last_h = draw.textsize(texts[-1], font=font)
		if last_w<50:
			n_font = font.size
			w, h = draw.textsize(text, font=font)
			while w>(2048-80*2):
				font.size = n_font
				w, h = draw.textsize(text, font=font)
				n_font -= 1

		if len(texts)>1:
			for cnt, t in enumerate(texts):
				w, h = draw.textsize(t, font=font)
				add_shadow((2048-x)/2 - w/2, y + addition, t, (112,112,112), font, draw)
				draw.text(((2048-x)/2 - w/2, y + addition), t, (255,255,255), font=font)
				if cnt+1<len(texts):
					addition += font.size + 13
		else:
			w, h = draw.textsize(text, font=font)
			add_shadow((2048-x)/2 - w/2, y+ addition, text, (112,112,112), font, draw)
			draw.text(((2048-x)/2 - w/2, y+ addition), text, (255,255,255), font=font)
		
		if x==0: 
			addition = 0

	return img

def add_shadow(x, y, text, shadowColor, font, draw):

	adj = 1
	#move right
	draw.text((x-adj, y), text, font=font, fill=shadowColor)
	#move left
	draw.text((x+adj, y), text, font=font, fill=shadowColor)
	#move up
	draw.text((x, y+adj), text, font=font, fill=shadowColor)
	#move down
	draw.text((x, y-adj), text, font=font, fill=shadowColor)
	#diagnal left up
	draw.text((x-adj, y+adj), text, font=font, fill=shadowColor)
	#diagnal right up
	draw.text((x+adj, y+adj), text, font=font, fill=shadowColor)
	#diagnal left down
	draw.text((x-adj, y-adj), text, font=font, fill=shadowColor)
	#diagnal right down
	draw.text((x+adj, y-adj), text, font=font, fill=shadowColor)

if __name__ == '__main__':
   app.run(debug = True)
