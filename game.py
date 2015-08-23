#!/usr/bin/python
# coding=UTF-8

import math

from pyglet import gl

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
		self._pad = 600,600
		self._interp = 1.0
		self._offset = 0, 0
		self.id = 'camera-controller'

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

	def initCamera(self,camera):
		self._interp = 1
		self.updateCamera(camera)

	def updateCamera(self,camera):
		GameEntity.mixin.CameraTarget.updateCamera(self,camera)
		iscale = 1.0/camera.scale
		itarget_scale = max(self._target_size[0]/camera.size[0],self._target_size[1]/camera.size[1])
		camera.scale = 1.0/(self._interp * itarget_scale + (1.0-self._interp) * iscale)

class PlayerBase(GameEntity,GameEntity.mixin.Movement,GameEntity.mixin.Animation):
	_MOVEMENT_LIMIT_BOTTOM = -100
	_MOVEMENT_LIMIT_LEFT = -1000
	_MOVEMENT_LIMIT_RIGHT = 1000

	FIGHTER_NAME = 'Anonymous'

	events = [
		('state-change','on_state_change'),
		('jump','on_jump'),
		('hit','on_hit'),
		('block','on_block'),
		('smash','on_smash'),
		('throw','on_throw'),
		('special','on_special'),
		('hurt','on_hurt')
	]

	def spawn(self):
		self.addTags('camera-target','player')

		self.state = 'standing'
		self.animation = 'stand'

		self.width = 100
		self.height = 200

		self.defence_level = 0

		self.health = 100.0

		self._action_timeout = self.game.currentTime

		self.move = {}

	def actionTimeoutAtLeast(self,timeout):
		self._action_timeout = max(self._action_timeout,self.game.currentTime+timeout)

	def checkActionTimeout(self):
		return self._action_timeout < self.game.currentTime

	def update(self,dt):
		self.velocity = self.velocity[0], self.velocity[1] - 2000 * dt
		if self.position[1] <= PlayerBase._MOVEMENT_LIMIT_BOTTOM \
			and self.state not in ('block','lying'):
			self.changeState('standing')
		self.position = min(PlayerBase._MOVEMENT_LIMIT_RIGHT,max(PlayerBase._MOVEMENT_LIMIT_LEFT,self.position[0])), \
						max(PlayerBase._MOVEMENT_LIMIT_BOTTOM,self.position[1])
		if self.id == 'player-right':
			left = self.game.getEntityById('player-left')
			if (self.position[0]-self.width/2) <= (left.position[0]+left.width/2):
				self.velocity = 0, self.velocity[1]
				# if self.state == 'standing':
				# 	self.animation = 'stand'
				self.position = left.position[0]+(left.width+self.width)/2, self.position[1]
		elif self.id == 'player-left':
			right = self.game.getEntityById('player-right')
			if (self.position[0]+self.width/2) >= (right.position[0]-right.width/2):
				self.velocity = 0, self.velocity[1]
				# if self.state == 'standing':
				# 	self.animation = 'stand'
				self.position = right.position[0] - (self.width + right.width)/2, self.position[1]
		self.update_go()

	def changeState(self,to,fromState=None):
		if fromState is None or fromState == self.state:
			if self.state != to:
				self.state = to
				self.trigger('state-change')

	def on_state_change(self):
		self.defence_level = 0
		self.consoleInfo('state <- ',self.state)
		if self.state == 'jump':
			self.animation = 'jump'
		elif self.state == 'block':
			self.defence_level = 10
		elif self.state == 'lying':
			self.animation = 'lying'
		else:
			self.animation = 'stand'

	def hurt(self,hurter):
		if self.defence_level < hurter.level:
			self.health -= hurter.damage
			self.trigger('hurt',hurter.damage)
			idst = distance(self.position,hurter.position)
			self.velocity = self.velocity[0], self.velocity[1] + 1000*(self.position[1] - hurter.position[1])/idst
		else:
			k = hurter.level / self.defence_level

		if self.health <= 0:
			self.health = 0
			# TODO: player defeat
			self.game.unsetEntityTags(self,'camera-target')
			self.changeState('lying')
			self.game.trigger('win',hurter.owner)
			return

	def specialAvailiable(self):
		return False

	def update_go(self):
		vx = 0
		if self.checkActionTimeout() and self.state != 'lying':
			for d,t in self.move.items():
				if t:
					vx += d
			vx *= 1000
		self.velocity = vx, self.velocity[1]

	def do_go(self,direction):
		if self.state != 'lying':
			self.move[direction] = True

	def stop_go(self,direction):
		self.move[direction] = False

	def do_hit(self):
		if (not self.checkActionTimeout()) or self.health <= 0:
			return
		self.animation = 'hit'
		if self.state == 'standing':
			self.actionTimeoutAtLeast(0.5)
			self.game.scheduleAfter(0.2, self.event('hit'))
		elif self.state == 'jump':
			self.actionTimeoutAtLeast(1)
			self.game.scheduleAfter(0.2, self.event('smash'))

	def do_block(self):
		if not self.checkActionTimeout():
			return
		if self.state == 'standing':
			self.changeState('block')
			self.consoleInfo('block start')
			self.trigger('block')
			self.animation = 'block'

	def stop_block(self):
		self.consoleInfo('block end')
		self.changeState(to='standing',fromState='block')

	def do_throw(self):
		if not self.checkActionTimeout():
			return
		if self.state in ('standing','block'):
			self.changeState('standing')
			self.animation = 'throw'
			self.actionTimeoutAtLeast(2.4)
			self.game.scheduleAfter(0.2, self.event('throw'))

	def do_special(self):
		if not self.checkActionTimeout():
			return
		if self.specialAvailiable():
			self.trigger('special')

	def do_jump(self):
		if not self.checkActionTimeout():
			return
		if self.state in ('standing','block'):
			self.velocity = self.velocity[0], 1000
			self.changeState('jump')
			self.trigger('jump')

	def faceToTarget(self, x):
		return x if (self.id == 'player-left') else -x

	def consoleInfo(self,*args):
		GAME_CONSOLE.write("{} ({}) ".format(self.FIGHTER_NAME,self.id),*args)


class Hurter(GameEntity,GameEntity.mixin.Movement,GameEntity.mixin.Sprite):
	'''
	Причинятор ущерба.
	'''
	@staticmethod
	def static_init(game,owner,position,velocity,ttl,damage,radius,level):
		self = Hurter()
		game.addEntity(self)

		self.position = position
		self.velocity = velocity
		self.owner = owner
		self.damage = damage
		self.radius = radius
		self.level = level
		game.scheduleAfter(ttl,self.destroy)
		self.sprite = "rc/img/32x32fg.png"
		self.scale = (self.radius/16.0)
		return self

	def spawn(self):
		self.addTags('hurter')

	def intersectsPlayer(self,player):
		px,py = player.position
		x,y = self.position
		return (x-self.radius < px+player.width/2) and\
			   (x+self.radius > px-player.width/2) and\
			   (y-self.radius < py+player.height/2) and\
			   (y+self.radius > py-player.height/2)

	def update(self,dt):
		for player in self.game.getEntitiesByTag('player'):
			if player != self.owner:
				if self.intersectsPlayer(player):
					player.hurt(self)
					self._sprite = None
					self.destroy()


@GameEntity.defineClass('static-entity')
class StaticEntity(GameEntity,GameEntity.mixin.Sprite):
	'''
	Просто статическая спрайтовая сущность с нестандартным z-индексом.
	'''
	z_index = -1

@GameEntity.defineClass('background-entity')
class BGEntity(GameEntity,GameEntity.mixin.Sprite):
	z_index = -2

	def on_configured(self):
		self._base_pos = self.position

	def update(self,dt):
		ctl = self.game.getEntityById('camera-controller')
		if ctl is not None:
			self.position = 0.5*(self._base_pos[0] + ctl.position[0]), \
							0.5*(self._base_pos[1] + ctl.position[1])

class GameLayer(GameLayer_):
	'''
	Наследник игрового слоя.
	'''
	_KEYMAP = {
		KEY.W : {'player': 'left', 'action': 'jump'},
		KEY.A : {'player': 'left', 'action': 'go', 'kw': {'direction':-1}},
		KEY.D : {'player': 'left', 'action': 'go', 'kw': {'direction':1}},
		KEY.Z : {'player': 'left', 'action': 'hit'},
		KEY.C : {'player': 'left', 'action': 'special'},
		KEY.V : {'player': 'left', 'action': 'throw'},
		KEY.B : {'player': 'left', 'action': 'block'},

		KEY.UP : {'player': 'right', 'action': 'jump'},
		KEY.LEFT : {'player': 'right', 'action': 'go', 'kw': {'direction':-1}},
		KEY.RIGHT : {'player': 'right', 'action': 'go', 'kw': {'direction':1}},
		KEY.NUM_1 : {'player': 'right', 'action': 'hit'},
		KEY.NUM_3 : {'player': 'right', 'action': 'special'},
		KEY.NUM_4 : {'player': 'right', 'action': 'throw'},
		KEY.NUM_5 : {'player': 'right', 'action': 'block'},
	}

	def init(self,*args,**kwargs):
		self._players = {
			'left':self._game.getEntityById('player-left'),
			'right':self._game.getEntityById('player-right')
			}
		self._camera_controller = self._game.getEntityById('camera-controller')
		self._camera.setController(self._camera_controller)

	def on_key_press(self,key,mod):
		'''
		Здесь происходит управление с клавиатуры.
		'''
		if key in GameLayer._KEYMAP:
			k = GameLayer._KEYMAP[key]
			kwa = k.get('kw',{})
			getattr(self._players[k['player']],'do_'+k['action'])(**kwa);

	def on_key_release(self,key,mod):
		if key in GameLayer._KEYMAP:
			k = GameLayer._KEYMAP[key]
			kwa = k.get('kw',{})
			fn = getattr(self._players[k['player']],'stop_'+k['action'],None)
			if fn is not None:
				fn(**kwa)

class ProgressBar(GUIItemLayer):
	LEFT_LAYOUT  = {'left': 10, 'top': 10,'height': 30,'width': 100}
	RIGHT_LAYOUT = {'right': 10,'top': 10,'height': 30,'width': 100}
	def init(self,grow_origin,expression,*args,**kwargs):
		self._expression = expression
		self._grow_origin = grow_origin
		self.back = _9Tiles(LoadTexture('rc/img/ui-frames.png'),Rect(left=12,bottom=0,width=12,height=12))
		self.front = _9Tiles(LoadTexture('rc/img/ui-frames.png'),Rect(left=12,bottom=0,width=12,height=12))
		self._inrect = None
		self._expRes = 65595

	def draw(self):
		self.back.draw(self.rect)
		k = self._expression()
		if self._inrect is None or k != self._expRes:
			self._inrect = self.rect.clone().inset(5).scale(scaleX=k,scaleY=1,origin=self._grow_origin)
			self._expRes = k

		if k > 0:
			self.front.draw(self._inrect)

	def on_layout_updated(self):
		self._inrect = None


@Screen.ScreenClass('STARTUP')
class StartupScreen(Screen):
	def init(self,*args,**kwargs):
		self.winner = None
		gl.glClearColor(0x1d/255.0,0x5b/255.0,0x70/255.0,1)

		# self.pushLayerFront(StaticBackgroundLauer('rc/img/256x256bg.png','fill'))

		game = Game()

		self.game = game

		game.loadFromJSON('rc/lvl/level0.json')

		game.listen('win')
		game.on('win',self.on_player_win)

		for pid in ('player-left','player-right'):
			p = (NaotaFighter() if pid == 'player-left' else HarukoFighter())
			game.addEntity(p)
			# p.animations = 'rc/ani/player-test-'+pid+'.json'
			p.position = 100 if pid == 'player-right' else -100, 0
			p.id = pid
			p.trigger('configured')

		self.gameLayer = GameLayer(game=game,camera=Camera())
		self.pushLayerFront(self.gameLayer)

		self.pushLayerFront(ProgressBar(grow_origin='top-left',
			expression=lambda: game.getEntityById('player-left').health / 100.0,
			layout=ProgressBar.LEFT_LAYOUT))
		self.pushLayerFront(ProgressBar(grow_origin='top-right',
			expression=lambda: game.getEntityById('player-right').health / 100.0,
			layout=ProgressBar.RIGHT_LAYOUT))

		GAME_CONSOLE.write('Startup screen created.')

	def on_key_press(self,key,mod):
		if key == KEY.ENTER and self.winner != None:
			self.next = StartupScreen()
		pass#GAME_CONSOLE.write('SSC:Key down:',KEY.symbol_string(key),'(',key,') [+',KEY.modifiers_string(mod),']')

	def on_player_win(self,player):
		GAME_CONSOLE.write('Player #',player.id,' wins.')
		self.winner = player
		class _GUITextItem(GUITextItem):
			def draw(self):
				self._label.draw()
		self.pushLayerFront(_GUITextItem(
			layout = {
				'width': 10,
				'height': 10,
				'bottom': 100
			},
			text=player.FIGHTER_NAME+' wins!'))
		self.pushLayerFront(_GUITextItem(
			layout = {
				'width': 10,
				'height': 10,
				'bottom': 50
			},
			text='Press ENTER to play again',
			fontSize=17))
		self.game.getEntityById('camera-controller')._pad = [player.width*3,player.height*3 ]

		for e in self.game.getEntitiesByTag('hurter'):
			e.damage = 0

		self.gameLayer.ignore('in:key:press')
		self.gameLayer.ignore('in:key:release')

class NaotaFighter(PlayerBase):
	FIGHTER_NAME = 'Naota'

	def on_configured(self):
		self.animations = 'rc/ani/fighter-naota-'+self.id+'.json'

	# def on_block(self):
	# 	self.defence_level = 10

	def on_hit(self):
		px,py=self.position
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=(px+self.faceToTarget(50),py),
			velocity=(self.faceToTarget(1000),0),
			ttl=0.150,damage=5,radius=16,level=1)
		ssound.Play('rc/snd/hit.wav')
		self.consoleInfo('strike')

	def on_hurt(self, damage):
		self.consoleInfo('damaged',damage)

	def on_smash(self):
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=(self.position[0]+self.faceToTarget(0),self.position[1]+200),
			velocity=(self.faceToTarget(1000),-2000),
			ttl=0.3,damage=15,radius=100,level=1)
		ssound.Play('rc/snd/smash.wav')
		self.consoleInfo('smashing')

	def on_throw(self):
		# время полёта в одну сторону подобрано в ручную
		local_ttl = 1.2
		FlyingGuitar.static_init(
			game=self.game,
			position=(self.position[0]+self.faceToTarget(100),self.position[1]-100),
			velocity=(self.faceToTarget(2000),0),
			angularVelocity=(self.faceToTarget(720)),
			sprite="rc/img/fg-boy-guitar.png",
			ttl=local_ttl
		)
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=(self.position[0]+self.faceToTarget(100),self.position[1]-100),
			velocity=(self.faceToTarget(2000),0),
			ttl=local_ttl,damage=19,radius=100,level=11)
		ssound.Play('rc/snd/chainsaw.wav')
		self.consoleInfo('throw')

	def on_jump(self):
		ssound.Play('rc/snd/hop.wav')

class HarukoFighter(PlayerBase):
	FIGHTER_NAME = 'Haruko'

	def on_configured(self):
		self.animations = 'rc/ani/fighter-haruko-'+self.id+'.json'

	# def on_block(self):
	# 	self.defence_level = 10

	def on_hit(self):
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=self.position,
			velocity=(self.faceToTarget(2000),0),
			ttl=0.150,damage=5,radius=16,level=1)
		ssound.Play('rc/snd/hit.wav')
		self.consoleInfo('strike')

	def on_hurt(self, damage):
		self.consoleInfo('damaged',damage)

	def on_smash(self):
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=(self.position[0]+self.faceToTarget(100),self.position[1]+200),
			velocity=(self.faceToTarget(1000),-2000),
			ttl=0.3,damage=15,radius=100,level=1)
		ssound.Play('rc/snd/smash.wav')
		self.consoleInfo('smashing')

	def on_throw(self):
		# время полёта в одну сторону подобрано в ручную
		local_ttl = 1.2
		FlyingGuitar.static_init(
			game=self.game,
			position=(self.position[0]+self.faceToTarget(100),self.position[1]-100),
			velocity=(self.faceToTarget(2000),0),
			angularVelocity=(self.faceToTarget(720)),
			sprite="rc/img/fg-girl-guitar.png",
			ttl=local_ttl
		)
		Hurter.static_init(
			game=self.game,
			owner=self,
			position=(self.position[0]+self.faceToTarget(100),self.position[1]-100),
			velocity=(self.faceToTarget(2000),0),
			ttl=local_ttl,damage=19,radius=100,level=11)
		ssound.Play('rc/snd/chainsaw.wav')
		self.consoleInfo('throw')

	def on_jump(self):
		ssound.Play('rc/snd/hu.wav')

class AtomskFighter(PlayerBase):
	FIGHTER_NAME = 'Atomsk'
	pass

class FlyingGuitar(GameEntity,GameEntity.mixin.Movement,GameEntity.mixin.Sprite):

	@staticmethod
	def static_init(game,position,velocity,angularVelocity,sprite,ttl):
		self = FlyingGuitar()
		game.addEntity(self)

		self.ttl = ttl
		self.position = position
		self.velocity = velocity
		self.angularVelocity = angularVelocity
		game.scheduleAfter(self.ttl, self.changeDirection)
		self.sprite = sprite
		self.spriteAnchor = 'center'
		# self.scale = (self.radius/16.0)
		return self

	def changeDirection(self):
		vx,vy =  self.velocity
		self.velocity = (-vx,vy)
		self.angularVelocity = - self.angularVelocity
		self.game.scheduleAfter(self.ttl, self.destroy)

music.Play("rc/snd/music/fourth.ogg")

GAME_CONSOLE.visible = False
