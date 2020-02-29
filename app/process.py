#  -*- coding: utf-8 -*- 
import re
import os
import io
import json
import shutil
import base64 
import datetime
import textwrap
import subprocess
import pandas as pd
import ChineseTone
from aip import AipSpeech
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
from flask import session
from werkzeug.utils import secure_filename

from config import *


def main(result):

	# Тухайн үгэнд зориулж шинэ хавтас үүсгэх
	word_download_path = '{language}/{word}'.format(language=session['language'],word=result.word.data)
	word_download_path = os.path.join(download_path, word_download_path)
	if not os.path.isdir(word_download_path):
		os.mkdir(word_download_path)

	# convert form object to dict
	result = update(result, word_download_path)

	# Зураг янзлах
	image_file = generate_image(result, word_download_path)

	# Дуу янзлах
	word_audio_file, example_audio_file = generate_audio(result, word_download_path)

	output_file = '{}.mp4'.format(result['word'])
	output_file = os.path.join(word_download_path, output_file)

	file_config = {
		'image': image_file,
		'word_audio': word_audio_file,
		'example_audio': example_audio_file,
		'output': output_file,
	}

	# Зураг ба дууг нийлүүлж mp4 үүсгэх
	mp4_file = get_mp4(file_config)

	return word_download_path, mp4_file


def save(f, fname, word_download_path):
    
    fname = fname + "." + secure_filename(f.filename).split('.')[-1]
    fname = os.path.join(word_download_path, fname)
    f.save(fname)
    
    return fname

def update(result, word_download_path):

	this = dict()
	for r in result.__iter__():

		if r.name in ['image', 'audio', 'audio_example'] and r.data:
			this[r.name] = save(r.data, r.name, word_download_path)
		elif r.name == 'cropped_image':
			img_data = r.data
			img_data = img_data[img_data.index('base64,')+len('base64,'):]

			img_file = os.path.join(word_download_path, 'cropped_image.png')
			with open(img_file, 'wb') as f:
				f.write(base64.b64decode(img_data))
			this[r.name] = img_file

		else:
			this[r.name] = r.data

	this['values'] = values[session['language']]

	if session['language']=="Chinese":

		if not this.get('pron', None):
			this['pron'] = ''.join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(this['word']))
		this['pron'] = this['pron'].replace(' ', '') 

		if not this.get('example_pron', None):
			this['example_pron'] = ' '.join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(this['example']))
		this['example_pron'] = re.sub(r'[。、！？，《》·：（）“”]', '', this['example_pron']) 

	return this

def get_mp4(file_config):

	if os.path.isfile(file_config['output']):
		os.remove(file_config['output'])

	if os.path.isfile(file_config['example_audio']):
		command = """
			ffmpeg -loop 1 \
				   -i {image} \
				   -i concat:{word_audio}|{example_audio} \
				   -crf 1 \
				   -t 10 \
				   -s 2048x2048 \
				   -vcodec libx264 \
				   -acodec aac \
				   -pix_fmt yuv420p \
				   {output}"""
	else:
		command = """
			ffmpeg -loop 1 \
				   -i {image} \
				   -i concat:{word_audio}|{word_audio}|{word_audio} \
				   -crf 1 \
				   -t 10 \
				   -s 2048x2048 \
				   -vcodec libx264 \
				   -acodec aac \
				   -pix_fmt yuv420p \
				   {output}"""

	subprocess.run(command.format(**file_config).split())

	return file_config['output'].split('/')[-1]

def generate_audio(result, word_download_path):

	word_audio_file = result['audio']
	example_audio_file = result['audio_example']

	if not word_audio_file:
		if session['language']=='Chinese':
			word_audio_file = generate_audio_chinese(result, word_download_path, result['word'], 'word')
			example_audio_file = generate_audio_chinese(result, word_download_path, result['example'], 'example')
	
	return word_audio_file, example_audio_file

def generate_audio_chinese(result, word_download_path, speech, _type):

	client = AipSpeech('17300058', 'G11hfH4f7Gzu8xSKdOUi5nGz', 'GGaF2RZfQGw3GdsMSbnP9oyTG1reMeqz')

	audio_file = None

	# per = random.choice([1,0,3,4,5,106,110,111,103])
	for per in [1,0,3,5,106][:1]: #,4,110,111,103]:
		try:
			audio_file = '{}_{}_{}_baidu.mp3'.format(result['word'], _type, per)
			audio_file = os.path.join(word_download_path, audio_file)
			audio_result = client.synthesis(speech,'zh',1,{'vol':10,'spd':4,'pit':5,'per':per})
			with open(audio_file, 'wb') as f:
				f.write(audio_result)
		except Exception as e:
			raise e

	return audio_file

def generate_image(result, word_download_path):

	# Зургийг нээх
	img = Image.open(result['cropped_image'])
	img = img.resize((2048, 2048))
	
	# Зургийг сүүдэрлэх
	enhancer = ImageEnhance.Brightness(img)
	img = enhancer.enhance(1 - 0.01 * int(result.get('shadow', 37)))

	# Зураг дээр текст хэлбэрийн агуулгыг нэмэх
	img = add_text(result, values, img)

	# Зураг дээр logo нэмэх
	logo = Image.open(logo_file)
	img.paste(logo, (920,1723), mask=logo)

	# Зургийг сануулах
	img.save(result['cropped_image'])

	return result['cropped_image']

def add_text(result, values, img):
	
	draw = ImageDraw.Draw(img)
	
	sizes = result['values']['sizes']
	fonts = result['values']['fonts']
	space = result['values']['default_space']

	if session['language'] in ['Chinese', 'Japanese']:
		values = [
				  (0,317,result['word'],fonts['word'],sizes['word']),
				  (0,582,'[%s] /%s/' % (result['pos'],result['pron']),fonts['pron'],sizes['pron']),
				  (0,826,result['mon'],fonts['mon'],sizes['mon']),
				  (80,1253,result['example_pron'],fonts['example_pron'],sizes['example_pron']),
				  (80,1253+sizes['example_pron']+space,result['example'],fonts['example'],sizes['example']),
				  (80,1253+sizes['example_pron']+space+sizes['example']+space,result['example_mon'],fonts['example_mon'],sizes['example_mon'])]

	elif session['language'] in ['English', 'German']:
		values = [
				  (0,317,result['word'],fonts['word'],sizes['word']),
				  (0,582,'[%s]   /%s/' % (result['pos'],result['pron']),fonts['pron'],sizes['pron']),
				  (0,826,result['mon'],fonts['mon'],sizes['mon']),
				  (80,1253,result['example'],fonts['example'],sizes['example']),
				  (80,1253+sizes['example']+space,result['example_mon'],fonts['example_mon'],sizes['example_mon'])]

	addition = 0
	for x, y, text, font_file, size in values:

		font_file = os.path.join(fonts_path, font_file)
		font = ImageFont.truetype(font_file, size)

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
		if last_w<300:
			n_size = size
			w, h = draw.textsize(text, font=font)
			while w>(2048-80*2):
				font = ImageFont.truetype(font_file, n_size)
				w, h = draw.textsize(text, font=font)
				n_size -= 1
			texts = [text]

		if len(texts)>1:
			for cnt, t in enumerate(texts):
				w, h = draw.textsize(t, font=font)
				add_shadow((2048 - w)/2, y + addition, t, (112,112,112), font, draw)
				draw.text(((2048 - w)/2, y + addition), t, (255,255,255), font=font)
				if cnt+1<len(texts):
					addition += font.size + 13
		else:
			w, h = draw.textsize(text, font=font)
			add_shadow((2048 - w)/2, y+ addition, text, (112,112,112), font, draw)
			draw.text(((2048 - w)/2, y+ addition), text, (255,255,255), font=font)
		
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
