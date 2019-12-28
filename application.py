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
import ChineseTone
from aip import AipSpeech
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
from flask import Flask, redirect, url_for, request, render_template, send_from_directory

app = Flask(__name__)

with open("custom_values.json", "r") as f:
	config = json.loads(f.read())

tmp_path = "tmp"
download_path = "data"

# Нүүр хуудас
@app.route("/")
def index():
   return render_template("index.html")
   
# Бүртгэлийн хуудас
@app.route("/login",methods = ["POST", "GET"])
def login():
	if request.method == "POST":
		user = request.form["nm"]
		return redirect(url_for("success",name = user))
	else:
		user = request.args.get("nm")
		return redirect(url_for("success",name = user))

# Хайчласан зургийг хадгалах, base64-с png болгох
@app.route("/save-crop",methods = ["POST", "GET"])
def save_crop():

	if request.method == "POST":

		result = request.get_json(silent=True, force=True)

		img_data = result["imgBase64"]
		img_data = img_data[img_data.index("base64,")+len("base64,"):]

		# tmp хавтаст хайчласан зургийг ха
		img_file = "{}.png".format(result["word"])
		img_file = os.path.join(tmp_path, img_file)

		with open(img_file, "wb") as tmp:
			tmp.write(base64.b64decode(img_data))

		return json.dumps({"success":True}), 200, {"ContentType":"application/json"} 

@app.route("/save-audio",methods = ["POST", "GET"])
def save_audio():

	if request.method == "POST":

		result = request.get_json(silent=True, force=True)

		audio_data = result["audioBase64"]

		audio_file = result["word"]
		if result["this_id"]=="audioExampleInput":
			audio_file += "_example"
		audio_file += ".mp3"
		audio_file = os.path.join(tmp_path, audio_file)

		with open(audio_file, "wb") as tmp:
			tmp.write(base64.b64decode(audio_data))

		return json.dumps({"success":True}), 200, {"ContentType":"application/json"} 

@app.route("/read-xls",methods = ["POST", "GET"])
def read_xls():

	if request.method == "POST":

		result = request.get_json(silent=True, force=True)

		SPREADSHEET_ID = config[result["lang"]]["sheets"]["SPREADSHEET_ID"]
		RANGE_NAME = config[result["lang"]]["sheets"]["RANGE_NAME"]

		df = google_sheets.main(SPREADSHEET_ID, RANGE_NAME)			
		for index, row in df.loc[df["word"] == result["word"]].iterrows():
			return json.dumps({"success":True,"row":[row.to_dict()]}), 200, {"ContentType":"application/json"} 

		return json.dumps({"success":False}), 400, {"ContentType":"application/json"} 

# mp4 бичлэгийг үүсгэх
@app.route("/generate",methods = ["POST", "GET"])
def generate():

	if request.method == "POST":
		result = dict(request.form)

		if result["lang"]=="Chinese":
			result = check_result_chinese(result)

		result["date"] = datetime.datetime.now().strftime("%Y%m%d") 
		
		# Тухайн үгэнд зориулж шинэ хавтас үүсгэх
		word_download_path = "{lang}/{word}_{date}".format(**result)
		word_download_path = os.path.join(download_path, word_download_path)
		if not os.path.isdir(word_download_path):
			os.mkdir(word_download_path)

		# Зураг янзлах
		image_file = generate_image(result, config, word_download_path)

		# Дуу янзлах
		word_audio_file, example_audio_file = generate_audio(result, word_download_path)
		if not os.path.isfile(word_audio_file):
			return json.dumps({"success":False, "error":"Please input the audio file"}), 500, {"ContentType":"application/json"} 

		# Зураг ба дууг нийлүүлж mp4 үүсгэх
		mp4_file = combine(result, word_download_path, image_file, word_audio_file, example_audio_file)

		word_file = "{}.txt".format(result["word"])
		word_file = os.path.join(word_download_path, word_file)		
		with open(word_file, "w") as f:
			json.dump(result, f, ensure_ascii=False)

		return send_from_directory(word_download_path, mp4_file, as_attachment=True)


def check_result_chinese(result):

	if not result.get("pron", None):
		result["pron"] = "".join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(result["word"]))

	result["pron"] = result["pron"].replace(" ", "") 

	if not result.get("example_pron", None):
		result["example_pron"] = " ".join(ChineseTone.PinyinHelper.convertToPinyinFromSentence(result["example"]))
	
	result["example_pron"] = re.sub(r"[。、！？，《》·：（）]", "", result["example_pron"]) 

	return result

def combine(result, word_download_path, image_file, word_audio_file, example_audio_file):

	output_file = "{}.mp4".format(result["word"])
	output_file = os.path.join(word_download_path, output_file)

	config = {
		"image": image_file,
		"word_audio": word_audio_file,
		"example_audio": example_audio_file,
		"output": output_file,
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

	return output_file.split("/")[-1]

def generate_audio(result, word_download_path):
	
	tmp_word_audio_file = os.path.join(tmp_path, "{}.mp3".format(result["word"]))
	tmp_example_audio_file = os.path.join(tmp_path, "{}_example.mp3".format(result["word"]))
	word_audio_file = os.path.join(word_download_path, "{}.mp3".format(result["word"]))
	example_audio_file = os.path.join(word_download_path, "{}_example.mp3".format(result["word"]))

	if os.path.isfile(tmp_word_audio_file):
		shutil.move(tmp_word_audio_file, word_audio_file)
	if os.path.isfile(tmp_example_audio_file):
		shutil.move(tmp_example_audio_file, example_audio_file)

	if not os.path.isfile(word_audio_file):
		if result["lang"]=="Chinese":
			word_audio_file = generate_audio_chinese(result, word_download_path, result["word"], "word")
			example_audio_file = generate_audio_chinese(result, word_download_path, result["example"], "example")
	
	return word_audio_file, example_audio_file

def generate_audio_chinese(result, word_download_path, speech, _type):

	client = AipSpeech("17300058", "G11hfH4f7Gzu8xSKdOUi5nGz", "GGaF2RZfQGw3GdsMSbnP9oyTG1reMeqz")

	audio_file = None

	# per = random.choice([1,0,3,4,5,106,110,111,103])
	for per in [1,0,3,5,106][:1]: #,4,110,111,103]:
		try:
			audio_file = "{}_{}_{}_baidu.mp3".format(result['word'], _type, per)
			audio_file = os.path.join(word_download_path, audio_file)
			audio_result = client.synthesis(speech,"zh",1,{"vol":10,"spd":4,"pit":5,"per":per})
			with open(audio_file, "wb") as f:
				f.write(audio_result)
		except Exception as e:
			raise e

	return audio_file

def generate_image(result, config, word_download_path):

	tmp_img_file = os.path.join(tmp_path, "{}.png".format(result["word"]))
	img_file = os.path.join(word_download_path, "{}.png".format(result["word"]))
	text_img_file = os.path.join(word_download_path, "{}_text.png".format(result["word"]))
	
	if os.path.isfile(tmp_img_file):
		shutil.move(tmp_img_file, img_file)

	# Хайчласан зургийг сууриар сонгох
	img = Image.open(img_file)
	img = img.resize((2048, 2048))
	
	# Зургийг сүүдэрлэх
	enhancer = ImageEnhance.Brightness(img)
	img = enhancer.enhance(1 - 0.01 * int(result["shadow"]))

	# Зураг дээр текст хэлбэрийн агуулгыг нэмэх
	img = add_text(result, config, img)

	# Зураг дээр logo нэмэх
	logo = Image.open("images/logo.png")
	img.paste(logo, (920,1723), mask=logo)

	# Зургийг сануулах
	img.save(text_img_file)

	return text_img_file

def add_text(result, config, img):
	
	draw = ImageDraw.Draw(img)
	
	sizes = config[result["lang"]]["sizes"]
	fonts = config[result["lang"]]["fonts"]
	space = config[result["lang"]]["default_space"]

	font_word = ImageFont.truetype(fonts["word_font"], int(sizes["word_size"]))
	font_pron = ImageFont.truetype(fonts["pron_font"], int(sizes["pron_size"]))
	font_mon = ImageFont.truetype(fonts["mon_font"], int(sizes["mon_size"])) 
	font_example_pron = ImageFont.truetype(fonts["example_pron_font"], int(sizes["example_pron_size"]))
	font_example = ImageFont.truetype(fonts["example_font"], int(sizes["example_size"])) 
	font_example_mon = ImageFont.truetype(fonts["example_mon_font"], int(sizes["example_mon_size"]))

	if result["lang"]=="Chinese":
		config = [
				  (0,317,result["word"],font_word),
				  (0,582,"[%s] /%s/" % (result["pos"],result["pron"]),font_pron),
				  (0,826,result["mon"],font_mon),
				  (80,1253,result["example_pron"],font_example_pron),
				  (80,1253+int(sizes["example_pron_size"])+space,result["example"],font_example),
				  (80,1253+int(sizes["example_pron_size"])+space+int(sizes["example_size"])+space,result["example_mon"],font_example_mon)]

	elif result["lang"]=="English":
		config = [
				  (0,317,result["word"],font_word),
				  (0,582,"[%s]   /%s/" % (result["pos"],result["pron"]),font_pron),
				  (0,826,result["mon"],font_mon),
				  (80,1253,result["example"],font_example),
				  (80,1253+int(sizes["example_pron_size"])+space,result["example_mon"],font_example_mon)]

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

if __name__ == "__main__":
   app.run(debug = True)
