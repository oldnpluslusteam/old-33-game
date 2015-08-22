#!/usr/bin/python
# coding=UTF-8

import math

from fwk.ui.screen import Screen
from fwk.ui.console import GAME_CONSOLE

from fwk.ui.layers.staticBg import StaticBackgroundLauer
from fwk.ui.layers.guiItem import GUIItemLayer
from fwk.ui.layers.guitextitem import GUITextItem
from fwk.ui.layers.gameLayer import GameLayer as GameLayer_
from fwk.ui.layers.texture9TileItem import *

from fwk.game.game import Game
from fwk.game.entity import GameEntity
from fwk.game.camera import Camera

import fwk.sound.static as ssound
import fwk.sound.music as music

from fwk.util.all import *

@GameEntity.defineClass('test-entity')
class TestEntity(GameEntity,GameEntity.mixin.Animation,GameEntity.mixin.Movement):
	def spawn(self):
		self.angularVelocity = 100
		self.i = 0
		self.think()
		self.addTags('camera-target')

	def think(self):
		# if self.i > 10:
		# 	return self.destroy()
		self.game.scheduleAfter(1.0,self.think)
		self.position = (self.i*10 % 40,-self.i*20 % 50)
		# self.velocity = (self.i*2353 % 200 - 100,-self.i*5423 % 350 - 175)
		self.velocity = (100*(-1 if self.i % 2 == 0 else 1),0)
		self.i += 1

@GameEntity.defineClass('camera-controller')
class FightingCameraController(GameEntity,GameEntity.mixin.CameraTarget):
	def spawn(self):
		self._target_focus = 0,0
		self._target_size = 100, 100
		self._pad = 50,50
		self._interp = 1.0
		self._offset = 0, 0

	def update(self,dt):
		targets = self.game.getEntitiesByTag('camera-target')

		p = self.position
		bl = self.position # min
		tr = self.position # max

		for target in targets:
			p = p[0] + target.position[0], p[1] + target.position[1]
			bl = min(bl[0], target.position[0]), min(bl[1], target.position[1])
			tr = max(tr[0], target.position[0]), max(tr[1], target.position[1])
		p = p[0] / float(len(targets)+1), p[1] / float(len(targets)+1)

		self.position = self._offset[0] + p[0] * self._interp + self.position[0] * (1.0 - self._interp), \
						self._offset[1] + p[1] * self._interp + self.position[1] * (1.0 - self._interp)

		self._target_size = 2*max(p[0]-bl[0],tr[0]-p[0]) + self._pad[0], 2*max(p[1]-bl[1],tr[1]-p[1]) + self._pad[1]
		self._interp = math.pow(2.0,dt-1.0) / 2.0

	def updateCamera(self,camera):
		GameEntity.mixin.CameraTarget.updateCamera(self,camera)
		iscale = 1.0/camera.scale
		itarget_scale = max(self._target_size[0]/camera.size[0],self._target_size[1]/camera.size[1])
		camera.scale = 1.0/(self._interp * itarget_scale + (1.0-self._interp) * iscale)

class PlayerBase(GameEntity,GameEntity.mixin.Movement,GameEntity.mixin.Animation):
	_MOVEMENT_LIMIT_BOTTOM = 0
	_MOVEMENT_LIMIT_LEFT = -100
	_MOVEMENT_LIMIT_RIGHT = 100

	def spawn(self):
		self.addTags('camera-target','player')

		self.state = 'standing'
		self.animation = 'stand'

		self.width = 100
		self.height = 200

		self.defence_level = 0

		self.healeh = 100.0

	def update(self,dt):
		self.velocity = self.velocity[0] - self.velocity[0] * dt, self.velocity[1] - 10
		self.position = min(PlayerBase._MOVEMENT_LIMIT_RIGHT,max(PlayerBase._MOVEMENT_LIMIT_LEFT,self.position[0])), \
						min(PlayerBase._MOVEMENT_LIMIT_BOTTOM,self.position[1])

	def hurt(self,hurter):
		if self.defence_level < hurter.level:
			self.healeh -= hurter.damage

	def do_go(self,direction):
		if self.state != 'lying':
			self.velocity = direction * 50, self.velocity[1]

	def do_hit(self):
		pass

	def do_smash(self):
		pass

	def do_throw(self):
		pass

	def do_special(self):
		pass

	def do_jump(self):
		if self.state == 'standing':
			self.velocity = self.velocity[0], 10

class Hurter(GameEntity,GameEntity.mixin.Movement):
	def __init__(self,game,owner,position,velocity,ttl,damage,radius,level):
		GameEntity.__init__(self)
		game.addEntity(self)

		self.position = position
		self.velocity = velocity
		self.owner = owner
		self.damage = damage
		self.radius = radius
		self.level = level
		game.scheduleAfter(ttl,self.destroy)

	def intersectsPlayer(self,player):
		pass #TODO: Искать пересечение с игроком

	def update(self,dt):
		for player in self.game.getEntitiesByTag('player'):
			if player != self.owner:
				if self.intersectsPlayer(player):
					player.hurt(self)
					self.destroy()

@GameEntity.defineClass('static-entity')
class StaticEntity(GameEntity,GameEntity.mixin.Sprite):
	'''
	Просто статическая спрайтовая сущность с нестандартным z-индексом.
	'''
	z_index = -1

class GameLayer(GameLayer_):
	'''
	Наследник игрового слоя.
	'''
	def init(self,*args,**kwargs):
		self._player = self._game.getEntityById('player')
		self._camera_controller = FightingCameraController()
		self._game.addEntity(self._camera_controller)
		self._camera.setController(self._camera_controller)

	def on_key_press(self,key,mod):
		'''
		Здесь происходит управление с клавиатуры.
		'''
		if key == KEY.UP:
			self._player.rotation += 20
		if key == KEY.DOWN:
			self._player.rotation -= 20

	def on_mouse_press(self,x,y,b,mod):
		'''
		Управление с мыши.
		'''
		self._player.position = self._camera.unproject((x,y))

	def draw(self):
		GameLayer_.draw(self)
		tep = self._camera.project(self._game.getEntityById('test0').position)
		DrawWireframeRect(Rect(left=tep[0],bottom=tep[1],width=100,height=100))


@Screen.ScreenClass('STARTUP')
class StartupScreen(Screen):
	def init(self,*args,**kwargs):

		# self.pushLayerFront(StaticBackgroundLauer('rc/img/256x256bg.png','fill'))

		game = Game()

		game.loadFromJSON('rc/lvl/level0.json')

		self.pushLayerFront(GameLayer(game=game,camera=Camera()))

		ssound.Preload('rc/snd/1.wav',['alias0'])

		musmap = {0:'rc/snd/music/Welcome.mp3',1:'rc/snd/music/Time.mp3',2:'rc/snd/music/0x4.mp3'}

		for x in xrange(0,3):
			layer = GUITextItem(
				layout={
					'width':100,
					'height':20,
					'left':50,
					'right':50,
					'offset_y':70*x,
					'padding':[20,10],
					'force-size':False
					},
				text=musmap[x]);
			layer.on('ui:click',(lambda x: lambda *a: music.Play(musmap[x],loop=True))(x))
			self.pushLayerFront(layer)

		tile = _9Tiles(LoadTexture('rc/img/ui-frames.png'),Rect(left=0,bottom=0,width=12,height=12))

		self.pushLayerFront(GUI9TileItem(
			tiles=tile,
			layout = {
				'left': 100,
				'right': 100,
				'top': 200,
				'bottom': 200
			}))

		GAME_CONSOLE.write('Startup screen created.')

	def on_key_press(self,key,mod):
		pass#GAME_CONSOLE.write('SSC:Key down:',KEY.symbol_string(key),'(',key,') [+',KEY.modifiers_string(mod),']')
