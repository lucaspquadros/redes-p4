class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


END = 0xC0
ESC = 0xDB
ESC_END = 0xDC
ESC_ESC = 0xDD

class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.receiving_buffer = bytearray()
        self.escape_sequence = False

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        quadro = bytearray()
        quadro.append(END)  # Byte de inicio
        
        for byte in datagrama:
            if byte == END:
                quadro.append(ESC)
                quadro.append(ESC_END)
            elif byte == ESC:
                quadro.append(ESC)
                quadro.append(ESC_ESC)
            else:
                quadro.append(byte)
        
        quadro.append(END)  # Byte de fim
        
        self.linha_serial.enviar(quadro)

    def __raw_recv(self, dados):
        for byte in dados:
            if byte == END:
                if self.receiving_buffer:
                    try:
                        self.callback(bytes(self.receiving_buffer))
                    except Exception:
                        import traceback
                        traceback.print_exc()
                    finally:
                        self.receiving_buffer = bytearray()
                        self.escape_sequence = False
            elif self.escape_sequence:
                if byte == ESC_END:
                    self.receiving_buffer.append(END)
                elif byte == ESC_ESC:
                    self.receiving_buffer.append(ESC)
                self.escape_sequence = False
            elif byte == ESC:
                self.escape_sequence = True
            else:
                self.receiving_buffer.append(byte)
        