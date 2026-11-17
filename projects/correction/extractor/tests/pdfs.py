"""PDFs mínimos gerados no teste, para não versionar PDFs de terceiros nem mandar dados reais."""


def make_pdf(lines: list[str], *, padding_bytes: int = 0, extra: tuple[str, ...] = ()) -> bytes:
    """PDF de uma página com uma linha de texto (Helvetica) por item; sem linhas, a página fica
    só com um retângulo e nenhum texto. `padding_bytes` engorda o arquivo com um comentário, e
    `extra` acrescenta trechos desenhados à parte (ver `hidden`)."""
    if lines:
        commands = ["BT", "/F1 10 Tf", "13 TL", "60 750 Td"]
        commands += [f"({_escape(line)}) Tj T*" for line in lines]
        commands.append("ET")
    else:
        commands = ["0 0 1 rg 100 100 200 200 re f"]
    commands += extra
    stream = "\n".join(commands).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    if padding_bytes:
        pdf += b"%" + b"x" * padding_bytes + b"\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(pdf)


def hidden(
    text: str, *, color: str = "0 g", size: float = 10, x: float = 60, y: float = 300
) -> str:
    """Um trecho desenhado com a cor (operador PDF, ex. "1 1 1 rg"), o tamanho e a posição
    dados, isolado do resto da página por q/Q."""
    return f"q BT /F1 {size} Tf {color} {x} {y} Td ({_escape(text)}) Tj ET Q"


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


# Artigo inventado, curto, com resumo, duas seções e referências.
ARTICLE_LINES = [
    "Medicao do tempo de resposta em filas de mensagens",
    "Ana Souza, Bruno Lima",
    "Resumo",
    "Este artigo mede o tempo de resposta de filas de mensagens sob carga constante.",
    "1 Introducao",
    "Filas de mensagens desacoplam produtores e consumidores [1].",
    "2 Resultados",
    "A mediana do tempo de resposta ficou abaixo de dez milissegundos.",
    "Referencias",
    "[1] C. Pereira. Sistemas distribuidos na pratica. Editora Exemplo, 2020.",
]
