# Bibliotecas
import pygame
import sys
import math
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Configurações da janela
LARGURA, ALTURA = 800, 600
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
VERMELHO = (200, 50, 50)
VERDE = (50, 200, 50)
AZUL = (50, 50, 200)

# Pêndulo
COMPRIMENTO_PENDULO = 150  # comprimento da haste em pixels
ANGULO_MAXIMO = math.radians(30)  # 30 graus para radianos em cada lado

# Física
FATOR_G = 0.003            # Fator de gravidade (0.003 é um bom valor)
FATOR_H = 0.001            # Fator de acoplamento (0.001 é um bom valor)
VEL_CARRINHO_MAX = 5       # Velocidade máxima do carrinho em pixels por frame

pygame.init()
fonte = pygame.font.SysFont("Comic Sans MS", 24)
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Pêndulo Invertido")
relogio = pygame.time.Clock()

# Música de fundo
pygame.mixer.init()
pygame.mixer.music.load("music/musica.wav")
pygame.mixer.music.play(-1)  # -1 para repetir indefinidamente
som_gameover = pygame.mixer.Sound("music/game_over.mp3")

caminho_img_carrinho = "img/carrinho.png"
img_carrinho = pygame.image.load(caminho_img_carrinho).convert_alpha()
largura_carrinho = img_carrinho.get_width()
altura_carrinho = img_carrinho.get_height()


def desenhar_texto(texto, cor, y, centralizado=True, x=10):
    render = fonte.render(texto, True, cor)
    if centralizado:
        rect = render.get_rect(center=(LARGURA // 2, y))
    else:
        rect = render.get_rect(topleft=(x, y))
    tela.blit(render, rect)


class Botao:
    def __init__(self, texto, x, y, w, h, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.texto = texto
        self.callback = callback

    def desenhar(self):
        pygame.draw.rect(tela, AZUL, self.rect)
        desenhar_texto(self.texto, BRANCO, self.rect.centery)

    def tratar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(evento.pos):
            self.callback()


class CaixaSelecao:
    def __init__(self, x, y, opcoes, selecionado, callback):
        self.x = x  # Posição x da caixa de seleção
        self.y = y  # Posição y da caixa de seleção
        self.opcoes = opcoes  # lista de tuplas (nome, valor)
        self.selecionado = selecionado
        self.callback = callback
        self.altura_opcao = 36  # Altura de cada opção
        self.largura = 180  # Largura da caixa de seleção

    def desenhar(self):
        for i, (nome, valor) in enumerate(self.opcoes):
            rect = pygame.Rect(
                self.x, self.y + i * self.altura_opcao, self.largura, self.altura_opcao - 4)
            cor_fundo = (200, 200, 255) if self.selecionado == valor else (
                230, 230, 230)
            pygame.draw.rect(tela, cor_fundo, rect, border_radius=8)
            pygame.draw.rect(tela, AZUL, rect, 2, border_radius=8)
            # Desenhar "bolinha" de seleção
            cx = self.x + 18
            cy = self.y + i * self.altura_opcao + self.altura_opcao // 2
            pygame.draw.circle(tela, AZUL, (cx, cy), 10, 2)
            if self.selecionado == valor:
                pygame.draw.circle(tela, AZUL, (cx, cy), 6)
            # Texto
            texto_render = fonte.render(nome, True, PRETO)
            texto_rect = texto_render.get_rect()
            texto_rect.topleft = (self.x + 38, self.y + i * self.altura_opcao +
                                  (self.altura_opcao - 4 - texto_rect.height) // 2)
            tela.blit(texto_render, texto_rect)

    def tratar_evento(self, evento):
        if evento.type == pygame.MOUSEBUTTONDOWN:
            mx, my = evento.pos
            for i, (nome, valor) in enumerate(self.opcoes):
                rect = pygame.Rect(
                    self.x, self.y + i * self.altura_opcao, self.largura, self.altura_opcao - 4)
                if rect.collidepoint(mx, my):
                    self.selecionado = valor
                    self.callback(valor)
                    break


class ControladorFuzzy:
    def __init__(self, conjuntos_saida=3):
        # Universo das variáveis
        self.angulo = ctrl.Antecedent(
            np.arange(-ANGULO_MAXIMO, ANGULO_MAXIMO+0.01, 0.01), 'angulo')

        self.velocidade = ctrl.Antecedent(
            np.arange(-FATOR_G*math.sin(ANGULO_MAXIMO), FATOR_G*math.sin(ANGULO_MAXIMO)+0.0001, 0.0001), 'velocidade')

        self.saida = ctrl.Consequent(
            np.arange(-VEL_CARRINHO_MAX, VEL_CARRINHO_MAX+1, 1), 'saida')

        # Funções de pertinência para ângulo
        self.angulo.automf(3, names=['neg', 'zero', 'pos'])

        # Funções de pertinência para velocidade angular
        self.velocidade.automf(3, names=['neg', 'zero', 'pos'])

        # Funções de pertinência para saída (movimento do carrinho)
        if conjuntos_saida == 3:
            self.saida.automf(3, names=['esq', 'zero', 'dir'])
            # Regras fuzzy para 3 conjuntos
            regras = [
                ctrl.Rule(self.angulo['neg'] &
                          self.velocidade['neg'], self.saida['esq']),
                ctrl.Rule(self.angulo['neg'] &
                          self.velocidade['zero'], self.saida['esq']),
                ctrl.Rule(self.angulo['neg'] &
                          self.velocidade['pos'], self.saida['zero']),

                ctrl.Rule(self.angulo['zero'] &
                          self.velocidade['neg'], self.saida['esq']),
                ctrl.Rule(self.angulo['zero'] &
                          self.velocidade['zero'], self.saida['zero']),
                ctrl.Rule(self.angulo['zero'] &
                          self.velocidade['pos'], self.saida['dir']),

                ctrl.Rule(self.angulo['pos'] &
                          self.velocidade['neg'], self.saida['zero']),
                ctrl.Rule(self.angulo['pos'] &
                          self.velocidade['zero'], self.saida['dir']),
                ctrl.Rule(self.angulo['pos'] &
                          self.velocidade['pos'], self.saida['dir']),
            ]
        else:
            self.saida.automf(
                7, names=['muito_esq', 'esq', 'pouco_esq', 'zero', 'pouco_dir', 'dir', 'muito_dir'])
            # Regras fuzzy para 7 conjuntos
            regras = [
                ctrl.Rule(
                    self.angulo['neg'] & self.velocidade['neg'], self.saida['muito_esq']),
                ctrl.Rule(self.angulo['neg'] &
                          self.velocidade['zero'], self.saida['esq']),
                ctrl.Rule(self.angulo['neg'] &
                          self.velocidade['pos'], self.saida['zero']),

                ctrl.Rule(
                    self.angulo['zero'] & self.velocidade['neg'], self.saida['pouco_esq']),
                ctrl.Rule(self.angulo['zero'] &
                          self.velocidade['zero'], self.saida['zero']),
                ctrl.Rule(
                    self.angulo['zero'] & self.velocidade['pos'], self.saida['pouco_dir']),

                ctrl.Rule(self.angulo['pos'] &
                          self.velocidade['neg'], self.saida['zero']),
                ctrl.Rule(self.angulo['pos'] &
                          self.velocidade['zero'], self.saida['dir']),
                ctrl.Rule(
                    self.angulo['pos'] & self.velocidade['pos'], self.saida['muito_dir']),
            ]

        sistema = ctrl.ControlSystem(regras)
        self.simulador = ctrl.ControlSystemSimulation(sistema)

    def calcular_saida(self, angulo, velocidade):
        self.simulador.input['angulo'] = angulo
        self.simulador.input['velocidade'] = velocidade
        self.simulador.compute()
        return self.simulador.output['saida']


class Jogo:
    def __init__(self, fuzzy_ativo=False, conjuntos_saida=3):
        self.carrinho_x = LARGURA // 2
        self.carrinho_y = ALTURA - 100
        self.fuzzy_ativo = fuzzy_ativo
        self.angulo = np.random.uniform(-math.radians(10), math.radians(10))
        self.velocidade_angular = 0
        self.vel_carrinho = 0
        self.game_over = False
        self.conjuntos_saida = conjuntos_saida
        self.controlador_fuzzy = ControladorFuzzy(
            conjuntos_saida) if fuzzy_ativo else None

    def atualizar(self, teclas):
        velocidade_carrinho = 0

        # Movimento manual
        if teclas[pygame.K_LEFT]:
            velocidade_carrinho -= VEL_CARRINHO_MAX
        if teclas[pygame.K_RIGHT]:
            velocidade_carrinho += VEL_CARRINHO_MAX

        # Movimento automático fuzzy (soma ao manual)
        if self.fuzzy_ativo and self.controlador_fuzzy and not self.game_over:
            saida_fuzzy = self.controlador_fuzzy.calcular_saida(
                self.angulo, self.velocidade_angular)
            velocidade_carrinho += saida_fuzzy  # saída do controlador fuzzy

        # Atualiza posição do carrinho com a velocidade calculada
        self.carrinho_x += velocidade_carrinho

        self.vel_carrinho = velocidade_carrinho

        # Limites de movimento do carrinho
        self.carrinho_x = max(40, min(LARGURA - 40, self.carrinho_x))

        # Física do pêndulo com acoplamento #######################
        # Simula a aceleração angular causada pela gravidade.
        self.velocidade_angular += FATOR_G * math.sin(self.angulo)

        # Acopla o movimento do carrinho ao pêndulo.
        self.velocidade_angular -= velocidade_carrinho * \
            math.cos(self.angulo) * \
            FATOR_H

        self.angulo += self.velocidade_angular  # Atualiza o ângulo do pêndulo

        # Game over se passar do ângulo limite
        if abs(self.angulo) >= math.radians(90):
            self.game_over = True
            pygame.mixer.music.stop()
            som_gameover.play()

    def desenhar(self):
        tela.fill(BRANCO)

        # Carrinho
        tela.blit(
            img_carrinho,
            (self.carrinho_x - largura_carrinho // 2,
             self.carrinho_y - altura_carrinho // 2)
        )

        # Linha do chão
        pygame.draw.line(tela, (120, 120, 120),
                         (0, self.carrinho_y + altura_carrinho // 2), (LARGURA, self.carrinho_y + altura_carrinho // 2), 6)

        # Base do pêndulo é o pivô da imagem (meio superior do carrinho)
        pivote_x = self.carrinho_x
        pivote_y = self.carrinho_y - altura_carrinho // 2  # topo da imagem do carrinho

        # Posição do final da haste
        ponta_x = pivote_x + COMPRIMENTO_PENDULO * math.sin(self.angulo)
        ponta_y = pivote_y - COMPRIMENTO_PENDULO * math.cos(self.angulo)

        # Desenha a haste
        pygame.draw.line(tela, PRETO, (pivote_x, pivote_y),
                         (ponta_x, ponta_y), 5)

        # Leituras em tempo real
        angulo_graus = math.degrees(self.angulo)
        vel_angular_graus = math.degrees(self.velocidade_angular)
        desenhar_texto(f"Ângulo: {angulo_graus:.3f}°",
                       PRETO, 80, centralizado=False, x=20)
        desenhar_texto(
            f"Vel. angular: {vel_angular_graus:.3f} °/s", PRETO, 110, centralizado=False, x=20)
        # desenhar_texto(
        #     f"X do carrinho: {self.carrinho_x:.3f} px", PRETO, 140, centralizado=False, x=20)
        desenhar_texto(
            f"Vel. carrinho: {self.vel_carrinho:.3f} px/frame", PRETO, 140, centralizado=False, x=20)

        # Mensagem
        if not self.game_over:
            if abs(self.angulo) <= ANGULO_MAXIMO:
                desenhar_texto("Tudo sob controle!", VERDE, 240)
            if self.fuzzy_ativo:
                desenhar_texto("Controlador Fuzzy: ATIVO", AZUL, 40)
        else:
            desenhar_texto("GAME OVER", VERMELHO, 220)


class GerenciadorJogo:
    def __init__(self):
        self.estado = "menu"
        self.jogo = None
        self.fuzzy_ativo = False
        self.conjuntos_saida = 3
        self.botao_jogar = Botao(
            "Play", LARGURA//2 - 75, ALTURA//2 - 25, 150, 50, self.iniciar_jogo)
        self.botao_fuzzy = Botao(
            "Fuzzy: OFF", LARGURA//2 - 75, ALTURA//2 + 40, 150, 50, self.toggle_fuzzy)
        self.botao_ajuda = Botao(
            "Ajuda", LARGURA//2 - 75, ALTURA//2 + 95, 150, 50, self.abrir_ajuda)
        self.botao_creditos = Botao(
            "Créditos", LARGURA//2 - 75, ALTURA//2 + 150, 150, 50, self.abrir_creditos)
        self.botao_menu = Botao(
            "Menu", LARGURA//2 - 75, ALTURA//2 + 50, 150, 50, self.voltar_menu)
        # Caixa de seleção para conjuntos fuzzy da saída
        self.caixa_selecao = CaixaSelecao(
            LARGURA - 200, 100,
            [("3 conjuntos", 3), ("7 conjuntos", 7)],
            self.conjuntos_saida,
            self.alterar_conjuntos_saida
        )

    def iniciar_jogo(self):
        pygame.mixer.music.play(-1)
        self.estado = "jogando"
        self.jogo = Jogo(fuzzy_ativo=self.fuzzy_ativo,
                         conjuntos_saida=self.conjuntos_saida)

    def toggle_fuzzy(self):
        self.fuzzy_ativo = not self.fuzzy_ativo
        self.botao_fuzzy.texto = "Fuzzy: ON" if self.fuzzy_ativo else "Fuzzy: OFF"
        # Atualiza o controlador fuzzy do jogo atual, se estiver jogando
        if self.jogo:
            self.jogo.fuzzy_ativo = self.fuzzy_ativo
            if self.fuzzy_ativo:
                self.jogo.controlador_fuzzy = ControladorFuzzy(
                    self.conjuntos_saida)
            else:
                self.jogo.controlador_fuzzy = None

    def abrir_creditos(self):
        self.estado = "creditos"

    def abrir_ajuda(self):
        self.estado = "ajuda"

    def alterar_conjuntos_saida(self, valor):
        self.conjuntos_saida = valor
        # Atualiza o controlador fuzzy do jogo atual, se estiver jogando
        if self.jogo and self.jogo.fuzzy_ativo:
            self.jogo.conjuntos_saida = valor
            self.jogo.controlador_fuzzy = ControladorFuzzy(valor)

    def voltar_menu(self):
        pygame.mixer.music.play(-1)
        self.estado = "menu"
        self.jogo = None

    def tratar_evento(self, evento):
        if self.estado == "menu":
            self.botao_jogar.tratar_evento(evento)
            self.botao_fuzzy.tratar_evento(evento)
            self.botao_ajuda.tratar_evento(evento)
            self.botao_creditos.tratar_evento(evento)
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_SPACE:
                self.iniciar_jogo()

        elif self.estado == "jogando" and self.jogo.game_over:
            self.botao_menu.tratar_evento(evento)
            if evento.type == pygame.KEYDOWN and evento.key == pygame.K_r:
                self.iniciar_jogo()

        elif self.estado == "creditos" or self.estado == "ajuda":
            # Voltar ao menu ao clicar qualquer tecla
            if evento.type == pygame.MOUSEBUTTONDOWN or evento.type == pygame.KEYDOWN:
                self.voltar_menu()

        # Caixa de seleção só ativa se fuzzy estiver ativo e jogando
        if self.estado == "jogando" and self.fuzzy_ativo:
            self.caixa_selecao.tratar_evento(evento)

    def atualizar(self):
        teclas = pygame.key.get_pressed()
        if self.estado == "jogando" and self.jogo and not self.jogo.game_over:
            self.jogo.atualizar(teclas)

    def desenhar(self):
        if self.estado == "menu":
            tela.fill(BRANCO)
            desenhar_texto("PÊNDULO INVERTIDO", AZUL, 100)
            self.botao_jogar.desenhar()
            self.botao_fuzzy.desenhar()
            self.botao_ajuda.desenhar()
            self.botao_creditos.desenhar()
            desenhar_texto(
                "Use as setas (< >) para controlar o carrinho.", PRETO, 180)
            desenhar_texto(
                "Ative o controle fuzzy para equilibrar automaticamente.", PRETO, 220)
        elif self.estado == "jogando":
            self.jogo.desenhar()
            if self.jogo.game_over:
                desenhar_texto("Pressione R para reiniciar",
                               AZUL, ALTURA // 2)
                self.botao_menu.desenhar()
            # Caixa de seleção no topo direito se fuzzy ativo
            if self.fuzzy_ativo:
                desenhar_texto("Saída com:", PRETO, 60,
                               centralizado=False, x=LARGURA - 200)
                self.caixa_selecao.desenhar()

        elif self.estado == "creditos":
            tela.fill(BRANCO)
            desenhar_texto("CRÉDITOS", AZUL, 100)
            desenhar_texto(
                "Este projeto foi desenvolvido por Rômulo Rodrigues,", PRETO, 200)
            desenhar_texto(
                "acadêmico em Engenharia Elétrica pelo IFMA,", PRETO, 240)
            desenhar_texto(
                "como parte das atividades da disciplina de Automação Inteligente,", PRETO, 280)
            desenhar_texto(
                "sob orientação do Prof. Dr. Ginalber L. O. Serra.", PRETO, 320)
            desenhar_texto(
                "São Luís - MA, 2025.", PRETO, 380)
            desenhar_texto(
                "Clique em qualquer tecla para voltar.", VERMELHO, 510)

        elif self.estado == "ajuda":
            tela.fill(BRANCO)
            desenhar_texto("AJUDA", AZUL, 100)
            desenhar_texto("Objetivo:", PRETO, 180)
            desenhar_texto(
                "Mantenha o pêndulo equilibrado pelo maior tempo possível!", PRETO, 220)
            desenhar_texto("Controles:", PRETO, 300)
            desenhar_texto(
                "Use as setas do teclado para mover o carrinho para a esq. ou dir.", PRETO, 340)
            desenhar_texto(
                "Ative o controle fuzzy para que o sistema tente equilibrar auto.", PRETO, 380)
            desenhar_texto(
                "No modo fuzzy, altere o número de conjuntos de saída no topo direito.", PRETO, 420)
            desenhar_texto(
                "O jogo termina se o pêndulo cair além do limite de inclinação (90°).", PRETO, 460)
            desenhar_texto(
                "Clique em qualquer tecla para voltar.", VERMELHO, 540)


def main():
    gerenciador = GerenciadorJogo()

    while True:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            gerenciador.tratar_evento(evento)

        gerenciador.atualizar()
        gerenciador.desenhar()

        pygame.display.flip()
        relogio.tick(60)


if __name__ == "__main__":
    main()
