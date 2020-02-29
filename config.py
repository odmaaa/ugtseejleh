import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    # ...
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'ugtseejleh.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

logo_file = os.path.join(basedir, 'app/static/images/logo.png') 
tmp_path = os.path.join(basedir, 'app/tmp')
download_path = os.path.join(basedir, 'app/data')
fonts_path = os.path.join(basedir, 'app/static/fonts')

values = {
  "Chinese": {
    "sheets":{
      "SPREADSHEET_ID": "14mY0zLrTJRPEJTprBen3FOqw1MTjM875qHiL_YHl0TA",
      "RANGE_NAME": "新HSK5000词!A:J"
    },
  	"sizes":{
	  	"word": 220,
	  	"pron": 100,  
	  	"mon": 120,  
	  	"example_pron": 65,  
	  	"example": 90,  
	  	"example_mon": 70   		
  	},
  	"fonts":{
      "word": "simhei.ttf",
      "pron": "simhei.ttf",  
      "mon": "SF-Pro-Display-Medium.otf",
      "example_pron": "SF-Pro-Display-Regular.otf",
      "example": "simhei.ttf",  
      "example_mon": "SF-Pro-Display-Regular.otf"
  	},
    "default_space": 23
  },
  "English": {
    "sheets":{
      "SPREADSHEET_ID": "14UP7Baf7ipQl1Z0tYhCRop5s5RLvaSAenN6BmRYmv6Y",
      "RANGE_NAME": "Sheet1!A:I"
    },
  	"sizes":{
	  	"word": 220,
	  	"pron": 100,  
	  	"mon": 130,  
	  	"example_pron": 74,  
	  	"example": 74,  
	  	"example_mon": 74   		
  	},
  	"fonts":{
      "word": "HelveticaNeue Medium.ttf",
  		"pron": "HelveticaNeue.ttc",
      "mon": "SF-Pro-Display-Medium.otf",
      "example": "SF-Pro-Display-RegularItalic.otf",
      "example_pron": "SF-Pro-Display-Regular.otf",
      "example_mon": "SF-Pro-Display-Regular.otf"
  	},
    "default_space": 23
  },
  "Japanese": {
    "sheets":{
      "SPREADSHEET_ID": "14mY0zLrTJRPEJTprBen3FOqw1MTjM875qHiL_YHl0TA",
      "RANGE_NAME": "新HSK5000词2!A:O"
    },
  	"sizes":{
	  	"word": 220,
	  	"pron": 100,  
	  	"mon": 120,  
	  	"example_pron": 65,  
	  	"example": 90,  
	  	"example_mon": 70   		
  	},
  	"fonts":{
  		"": ""
  	},
    "default_space": 23
  },
  "German": {
    "sheets":{
      "SPREADSHEET_ID": "14mY0zLrTJRPEJTprBen3FOqw1MTjM875qHiL_YHl0TA",
      "RANGE_NAME": "新HSK5000词2!A:O"
    },
   	"sizes":{
	  	"word": 220,
	  	"pron": 100,  
	  	"mon": 120,  
	  	"example_pron": 65,  
	  	"example": 90,  
	  	"example_mon": 70   		
  	},
  	"fonts":{
  		"": ""
  	},
    "default_space": 23
  }
}
