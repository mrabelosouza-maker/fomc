"""Escreve data/extracted/powell-*-c0ef29.json para as 11 coletivas do Powell
desde 2025, na MESMA rubrica (registry/rubric.json) usada no resto do corpus.

Ancora de MENSAGEM, como os demais membros. Onde mensagem e entrega divergem
(29/10/2025: cortou e avisou que dezembro "nao e conclusao antecipada"), a
ressalva esta no summary, no mesmo padrao das fichas do Warsh.

    python scripts/score_powell_pressers.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fomc import config  # noqa: E402
from fomc.schema import speech_id  # noqa: E402

TITLE = "FOMC Press Conference"
URL = "https://www.federalreserve.gov/mediacenter/files/FOMCpresconf{key}.pdf"

D = lambda o, u, t, l, g, x: {                                    # noqa: E731
    "oil_war": o, "underlying_inflation": u, "tariffs": t,
    "labor_market": l, "growth_demand": g, "other": x}
H = lambda i: {"intensity": i, "push": "hawkish"}                 # noqa: E731
V = lambda i: {"intensity": i, "push": "dovish"}                  # noqa: E731
N = lambda i: {"intensity": i, "push": "neutral"}                 # noqa: E731

DOCS = [
{"key": "20250129", "comp": 1.0, "mand": 1.0, "infl": 2.5, "lab": 1.0, "stance": 3.5,
 "bias": ("hold", "patient"), "themes": ["tariffs", "immigration", "financial_stability", "r_star"],
 "drivers": D(N(0), H(2), N(2), N(2), H(2), N(2)),
 "summary": "Manutencao em 4,25-4,50% depois de 100bp de cortes em 2024. O fio condutor e a paciencia justificada pela forca da economia, nao pela confianca na desinflacao: com a postura 'significativamente menos restritiva' e a economia solida, 'nao precisamos ter pressa'. Ele enuncia uma funcao de reacao simetrica e explicita - se a economia seguir forte e a inflacao nao voltar a 2% de forma sustentavel, da para manter a restricao por mais tempo; se o emprego enfraquecer, da para afrouxar. Diagnostica a postura como 'meaningfully restrictive. Not highly restrictive' e o mercado de trabalho como 'broadly in balance' e nao fonte de pressao inflacionaria. Sobre tarifas, imigracao, fiscal e regulacao, recusa qualquer prejulgamento: e cedo, o leque de possibilidades e 'very, very wide'. Condicoes financeiras 'provavelmente ainda um pouco acomodaticias, mas e um quadro misto'. Leve vies hawkish pelo lado da recusa em cortar, nao por conviccao de inflacao.",
 "quotes": [
   ("With our policy stance significantly less restrictive than it had been and the economy remaining strong, we do not need to be in a hurry to adjust our policy stance.",
    "Remarks iniciais; a justificativa da pausa e a forca da economia somada aos 100bp ja entregues.", "composite_hawk_dove"),
   ("If the labor market were to weaken unexpectedly or inflation were to fall more quickly than anticipated, we can ease policy accordingly.",
    "Segunda metade da funcao de reacao simetrica que ele enuncia nas remarks; a primeira e manter a restricao por mais tempo se a inflacao nao ceder.", "near_term_bias"),
   ("we think that our policy stance is restrictive. Meaningfully restrictive. Not highly restrictive, but meaningfully restrictive.",
    "Resposta sobre o quanto falta para cortar; e a leitura de restritividade mais alta de todo o mandato dele no corpus.", "policy_stance_read"),
   ("The labor market is not a source of significant inflationary pressures.",
    "Fecha a secao de emprego das remarks; formula que ele repete em quase todas as coletivas de 2025 e que sustenta labor_concern baixo.", "labor_concern")]},

{"key": "20250319", "comp": 0.5, "mand": 0.5, "infl": 2.5, "lab": 1.5, "stance": 3.5,
 "bias": ("hold", "patient"), "themes": ["tariffs", "immigration", "balance_sheet_qt"],
 "drivers": D(N(0), H(2), H(3), N(2), N(2), N(2)),
 "summary": "Manutencao mais desaceleracao tecnica do QT. A palavra do dia e clareza: 'well positioned to wait for greater clarity', com a incerteza sobre comercio, imigracao, fiscal e regulacao declarada 'unusually elevated'. E aqui que ele formula a doutrina de look-through que Goolsbee viria a revogar em set/2026: pode ser apropriado olhar atraves da inflacao tarifaria SE ela passar rapido e SE as expectativas longas seguirem ancoradas - e as longas, diz, seguem ancoradas apesar do salto nas curtas. Reconhece que a inflacao de bens subiu 'pretty significantly' em jan-fev e que parte disso e tarifa, mas o SEP mantem dois cortes em 2025 porque crescimento menor e inflacao maior 'se cancelam'. Diagnostica a postura como 'clearly a restrictive stance'. Menos hawkish que janeiro: entra risco de baixa para atividade e a disposicao explicita de relevar o choque de oferta.",
 "quotes": [
   ("We do not need to be in a hurry to adjust our policy stance, and we are well positioned to wait for greater clarity.",
    "Frase-sintese das remarks; a pausa passa a ser justificada pela incerteza, nao mais so pela forca da economia.", "composite_hawk_dove"),
   ("it can be the case that it's appropriate sometimes to look through inflation if it's going to go away quickly without action by, by us, if it's transitory.",
    "A doutrina do look-through, com as duas condicoes que ele anexa (passar rapido e expectativas longas ancoradas). E o argumento que Goolsbee revoga em 21/09/2026.", "inflation_conviction"),
   ("we're at a place where we can cut or we - or we can hold what is a clearly a restrictive stance of policy.",
    "Definicao explicita de 'well positioned'; sustenta policy_stance_read em 3,5.", "policy_stance_read"),
   ("I do think with the arrival of, of the tariff inflation, further progress may be delayed",
    "Reconhece que a desinflacao para em 2025 por causa das tarifas - atraso, nao reversao.", "inflation_conviction")]},

{"key": "20250507", "comp": 0.5, "mand": 0.5, "infl": 3.0, "lab": 2.0, "stance": 3.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "fiscal"],
 "drivers": D(N(0), H(2), H(3), N(2), V(2), N(2)),
 "summary": "Manutencao unanime seis semanas depois do 2 de abril, com as tarifas anunciadas 'significativamente maiores do que o antecipado'. O documento e o mais equilibrado do conjunto: o comunicado passa a dizer que subiram OS DOIS riscos, de desemprego e de inflacao, e ele desenvolve pela primeira vez o protocolo para quando os mandatos entram em tensao (quao longe cada variavel esta da meta e quanto tempo levaria para voltar). Ainda assim, a conclusao operacional e hawkish na margem: ele recusa explicitamente um corte preventivo porque, ao contrario de 2019, 'a inflacao esta acima da meta ha quatro anos'. Fixa a obrigacao de impedir que um aumento de nivel de precos vire processo inflacionario. Postura 'modestly or moderately restrictive'. Emprego solido, sem deterioracao nos dados duros - apenas sentimento muito ruim.",
 "quotes": [
   ("The risks of higher unemployment and higher inflation appear to have risen",
    "Nova frase do comunicado; e o primeiro reconhecimento formal de que os dois lados do mandato pioraram ao mesmo tempo.", "composite_hawk_dove"),
   ("Our obligation is to keep longer-term inflation expectations well anchored and to prevent a one-time increase in the price level from becoming an ongoing inflation problem.",
    "A guarda hawkish que ele passa a repetir em todas as coletivas seguintes de 2025.", "mandate_weight"),
   ("it's not a situation where we can be preemptive, because we actually don't know what the right response to, to the data will be until we see more data.",
    "Recusa do corte preventivo, contrastando explicitamente com 2019, quando a inflacao estava em 1,6%.", "near_term_bias"),
   ("our policy is sort of modestly or moderately restrictive.",
    "Leitura da postura corrente, um degrau abaixo de janeiro.", "policy_stance_read")]},

{"key": "20250618", "comp": 1.0, "mand": 1.0, "infl": 3.0, "lab": 1.5, "stance": 3.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "ai_productivity", "immigration"],
 "drivers": D(V(1), H(2), H(3), N(2), N(2), N(2)),
 "summary": "Manutencao com o SEP marcando 3,0% de PCE cheio para 2025 (seis decimos acima de dezembro) e ainda dois cortes na mediana. O tom endurece em relacao a maio porque ele passa a defender a espera em termos de inflacao, nao de incerteza: 'temos de manter os juros altos para trazer a inflacao toda de volta', e a frase que resume a recusa em ceder, 'o mercado de trabalho nao esta pedindo corte de juros'. Argumenta que politica monetaria e necessariamente prospectiva e que todos os previsores esperam repasse tarifario relevante nos meses seguintes - por isso nao se pode olhar so o retrovisor, que 'levaria a uma postura neutra'. Postura corrente rebaixada mais um degrau, para 'probably modestly now - restrictive'. Sobre o Oriente Medio, aplica o look-through classico: choques de energia 'nao costumam ter efeitos duradouros sobre a inflacao' - diagnostico que os proprios 2026 desmentiriam.",
 "quotes": [
   ("we have to keep rates high to keep - to get inflation all the way down.",
    "Resposta a pergunta sobre o custo da espera para consumidores e pequenas empresas; e a defesa mais direta da postura restritiva em 2025.", "mandate_weight"),
   ("the labor market's not crying out for a rate cut.",
    "Sintese da razao pela qual ele nao cede: nao ha gatilho do lado do emprego.", "labor_concern"),
   ("I would say policy is modestly or moderately - probably modestly now - restrictive.",
    "Terceiro rebaixamento consecutivo da leitura de restritividade, com a justificativa de que a economia nao se comporta como sob politica muito apertada.", "policy_stance_read"),
   ("certainly, a hike is not the base case at all.",
    "Ultima resposta; delimita o vies - a espera e contra o corte, nao a favor da alta.", "near_term_bias")]},

{"key": "20250730", "comp": 2.0, "mand": 2.0, "infl": 3.0, "lab": 2.0, "stance": 3.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "fed_independence", "financial_stability"],
 "drivers": D(N(0), H(3), H(3), N(2), N(2), H(2)),
 "summary": "A coletiva mais hawkish do Powell em 2025, e a unica do ano em que o indice de lexico fica positivo. Manutencao com DUAS dissidencias pro-corte (Bowman e Waller) - as primeiras dissidencias duplas de governadores em decadas -, e ele responde com uma hierarquizacao aritmetica do mandato: a inflacao esta acima da meta, o emprego esta NA meta, logo a postura deve ser restritiva, porque 'politica apertada e o que traz a inflacao para baixo'. Acrescenta que 'as condicoes financeiras estao acomodaticias' e que a economia nao se comporta como se a politica a estivesse segurando indevidamente. Diz que o comunicado passa a descrever a postura como apropriada 'para se proteger contra riscos de inflacao'. Concede que ha risco de baixa no emprego - o equilibrio vem de oferta e demanda caindo juntas -, mas nao o trata como acionavel. Fecha com a promessa de que o repasse tarifario nao virara inflacao 'porque vamos garantir que nao'.",
 "quotes": [
   ("We see our current policy stance as appropriate to guard against inflation risks.",
    "Frase nova das remarks; e a formulacao mais explicitamente hawkish do ano.", "mandate_weight"),
   ("the majority view was, was still what it has been, which is that inflation is running above target, maximum employment is right at target.",
    "A aritmetica com que ele rebate as duas dissidencias pro-corte: uma variavel esta na meta, a outra nao.", "composite_hawk_dove"),
   ("Financial conditions are accommodative, and the economy is not - the economy is not performing as though restrictive policy were holding it back inappropriately.",
    "Argumento de FCI - o mesmo instrumento que Warsh usaria em 2026, aqui empregado para justificar manter, nao subir.", "policy_stance_read"),
   ("in the end, there should be no doubt that we will do what we need to do to keep inflation under control.",
    "Compromisso condicional: o repasse tarifario nao virara inflacao porque o Fed garantira que nao.", "inflation_conviction")]},

{"key": "20250917", "comp": -1.5, "mand": -1.5, "infl": 2.5, "lab": 3.5, "stance": 3.5,
 "bias": ("cut", "gradual"), "themes": ["tariffs", "immigration", "ai_productivity"],
 "drivers": D(N(0), H(2), H(2), V(3), N(2), N(2)),
 "summary": "O giro. Corte de 25bp para 4,00-4,25% com payrolls de 29 mil/mes na media de tres meses e desemprego em 4,3%. Ele chama de 'risk-management cut' e e explicito sobre o que mudou: nao a inflacao, mas a leitura do risco de emprego, que de risco virou realidade - 'eu disse que havia risco de baixa entao, mas agora esse risco de baixa e uma realidade'. Formaliza o criterio: quando os dois riscos se aproximam da igualdade, a postura deve caminhar para o neutro. Mantem o compromisso com 2% e observa que o risco de inflacao persistente 'provavelmente ficou um pouco menor' desde abril porque o repasse foi mais lento e menor do que se temia e o mercado de trabalho afrouxou. Rejeita 50bp. Nucleo em 2,9% e SEP com 3,0% para 2025. Dez dos 19 escreveram dois ou mais cortes no restante do ano; nove escreveram menos.",
 "quotes": [
   ("In the near term, risks to inflation are tilted to the upside and risks to employment to the downside - a challenging situation.",
    "Formulacao que passa a abrir todas as coletivas seguintes; e o enquadramento de choque de oferta com mandatos em tensao.", "composite_hawk_dove"),
   ("we judged it appropriate at this meeting to take another step toward a more neutral policy stance.",
    "Justificativa do corte: reequilibrio de riscos, nao mudanca no diagnostico de inflacao.", "near_term_bias"),
   ("you could think of this, in a way, as a risk-management cut",
    "Rotulo que ele mesmo da a decisao, apos notar que o SEP na verdade elevou o crescimento projetado.", "composite_hawk_dove"),
   ("we see that the labor market is softening, and we don't need it to soften any more, don't want it to.",
    "A frase que inverte a hierarquia de julho, quando o emprego 'estava na meta' e por isso nao acionava a politica.", "labor_concern")]},

{"key": "20251029", "comp": 0.0, "mand": -0.5, "infl": 2.5, "lab": 3.0, "stance": 3.0,
 "bias": ("hold", "data-dependent"), "themes": ["tariffs", "balance_sheet_qt", "ai_productivity"],
 "drivers": D(N(0), H(2), H(2), V(3), H(2), N(2)),
 "summary": "RESSALVA DE ANCORA: este e o documento do corpus em que mensagem e entrega mais divergem no conjunto do Powell, e na direcao oposta a da coletiva do Warsh de 29/07/2026. Ali houve retorica dura sem acao; aqui houve acao dovish (segundo corte de 25bp, para 3,75-4,00%, mais o fim do QT em 1o de dezembro) com orientacao dura: 'um novo corte em dezembro nao e uma conclusao antecipada - longe disso'. Foi a frase que reprecificou a curva no dia. Ele descreve 'visoes fortemente divergentes' no comite, com duas dissidencias em direcoes opostas (uma por 50bp, uma por nenhum corte) e um 'coro crescente' a favor de esperar um ciclo. Mantem o diagnostico de que a inflacao ex-tarifas 'nao esta tao longe' de 2% (2,3-2,4% contra 2,8% no cheio) e que o emprego segue esfriando de forma gradual, sem deterioracao. O composite fica em 0,0 justamente porque a acao e a orientacao se anulam.",
 "quotes": [
   ("A further reduction in the policy rate at the December meeting is not a foregone conclusion - far from it.",
    "Dita nas remarks preparadas e repetida na primeira resposta; e o conteudo marginal da coletiva e o que anula, na ancora de mensagem, o corte entregue.", "near_term_bias"),
   ("There is no risk-free path for policy as we navigate this tension between our employment and inflation goals.",
    "Formula do dilema de choque de oferta, repetida daqui em diante.", "composite_hawk_dove"),
   ("there's a growing chorus now of feeling like maybe this is where we should at least wait a cycle, something like that.",
    "Descricao do comite: depois de 150bp de corte, parte dos participantes quer parar para ver.", "policy_stance_read"),
   ("inflation away from tariffs is actually not so far from our 2 percent goal.",
    "Decomposicao que sustenta a leitura relativamente benigna de inflacao: 2,3-2,4% ex-tarifas contra 2,8% no nucleo cheio.", "inflation_conviction")]},

{"key": "20251210", "comp": -1.0, "mand": -1.0, "infl": 2.5, "lab": 3.5, "stance": 2.5,
 "bias": ("hold", "data-dependent"), "themes": ["tariffs", "ai_productivity", "balance_sheet_qt"],
 "drivers": D(N(0), H(2), H(2), V(3), H(2), N(2)),
 "summary": "Terceiro corte consecutivo, para 3,50-3,75%, por 9 a 3 - a votacao mais dividida do periodo. A entrega e dovish e a justificativa tambem: desemprego subiu para 4,4%, payrolls em 40 mil/mes desde abril e, ajustando pela sobrecontagem que o proprio staff estima, criacao liquida NEGATIVA de cerca de 20 mil. Ele diz que nao quer que a politica fique 'empurrando para baixo a criacao de emprego'. Mas o documento tambem marca o fim do ciclo de flexibilizacao: com 175bp acumulados, a taxa entra 'na faixa de estimativas plausiveis do neutro' - e ele especifica, 'na ponta alta dessa faixa' -, e a linguagem muda para 'bem posicionados para esperar e ver'. Nucleo em 2,8%, ex-tarifas 'nos 2 baixos'. Alta de juros 'nao e o caso-base de ninguem'. Vies liquido dovish pela acao, com a porta de saida ja aberta.",
 "quotes": [
   ("The adjustments to our policy stance since September bring it within a range of plausible estimates of neutral",
    "Remarks preparadas; o corte vem acompanhado da sinalizacao de que o espaco acabou.", "policy_stance_read"),
   ("Now we're in the range of neutral. We're in the high end of the range of neutral, I would say.",
    "Precisa a localizacao - ponta alta do neutro -, que e o que transforma o corte em possivel ultimo corte.", "near_term_bias"),
   ("I think a world where job creation is negative, I just think we need to watch that situation very carefully",
    "Justificativa do corte: criacao liquida de emprego negativa uma vez ajustada a sobrecontagem.", "labor_concern"),
   ("we're going to need to have some years where real compensation is higher",
    "Fecha a resposta sobre custo de vida; e a ligacao entre o mandato de emprego e o de precos que ele usa para defender o corte.", "mandate_weight")]},

{"key": "20260128", "comp": 1.5, "mand": 1.5, "infl": 3.0, "lab": 2.0, "stance": 2.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "ai_productivity", "fiscal", "fed_independence"],
 "drivers": D(N(1), H(3), H(3), N(2), H(3), N(2)),
 "summary": "Manutencao em 3,50-3,75% e o primeiro documento francamente hawkish do novo ciclo. Ele RETIRA do comunicado a frase de que os riscos de baixa para o emprego subiram, porque ha sinais de estabilizacao do desemprego, e registra 'melhora clara' na perspectiva de crescimento. Do lado dos precos, faz a conta que incomoda: nucleo de PCE em 3,0% nos 12 meses ate dezembro, praticamente o mesmo de um ano antes - 'no liquido, nenhum progresso'. E rebaixa a leitura da propria postura ate quase o neutro: 'e dificil olhar os dados que estao chegando e dizer que a politica esta significativamente restritiva'. A contrapartida dovish permanece verbal - houve dissidencias pro-corte e ele diz que os riscos dos DOIS lados diminuiram. Fecha com a advertencia de que as empresas do meio da cadeia seguem decididas a repassar o resto das tarifas, 'razao pela qual precisamos manter o olho na inflacao e nao declarar vitoria prematuramente'.",
 "quotes": [
   ("Having lowered our policy rate by 75 basis points over the course of our previous three meetings, we see the current stance of monetary policy as appropriate",
    "Remarks; a pausa e apresentada como resultado do ciclo ja entregue, nao como espera por dados.", "composite_hawk_dove"),
   ("it's hard to look at the incoming data and say that policy's significantly restrictive at this time.",
    "Primeira vez que ele se aproxima da posicao que Warsh radicalizaria em 2026 - a de que a politica nao esta restritiva.", "policy_stance_read"),
   ("And that's pretty much what we had the year before. So, on net, no progress.",
    "Sobre o nucleo de PCE em 3,0% nos 12 meses ate dezembro; o balanco de um ano inteiro sem desinflacao.", "inflation_conviction"),
   ("which is one of the reasons why we need to keep our eye on inflation and not declare victory prematurely.",
    "Ultima resposta da coletiva, sobre as empresas do meio da cadeia que ainda pretendem repassar tarifas.", "mandate_weight")]},

{"key": "20260318", "comp": 2.0, "mand": 2.0, "infl": 3.5, "lab": 2.0, "stance": 2.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "ai_productivity", "r_star"],
 "drivers": D(H(3), H(3), H(3), N(2), H(2), N(2)),
 "summary": "Manutencao com o choque do Oriente Medio ja dentro dos precos. O movimento decisivo e ele CONDICIONAR o look-through de energia: 'a questao de olhar atraves da inflacao de energia so se coloca depois de termos marcado aquele quadrinho' - isto e, depois de ver a desinflacao de bens prometida pelas tarifas. E acrescenta a segunda condicao, que Warsh levaria ao limite: o look-through classico depende das expectativas ancoradas e agora tambem do contexto de 'cinco anos de inflacao acima da meta'. Contabiliza os choques em serie - pandemia, tarifas, energia - e diz que e exatamente esse padrao repetido que ameaca as expectativas. Revela que a possibilidade de a proxima decisao ser ALTA foi discutida na reuniao, como ja fora na anterior. Nucleo em 3,0%, 'um ponto percentual inteiro acima de 2% ha algum tempo. E isso e uma preocupacao'. A mediana do SEP nao muda, mas quatro ou cinco participantes migram de dois cortes para um. Postura corrente: 'ponta alta do neutro ou talvez levemente restritiva'.",
 "quotes": [
   ("The question of whether we \"look through\" the energy inflation doesn't really arise until we have kind of checked that box.",
    "Condiciona o look-through de energia a ver antes a desinflacao de bens prometida; e o primeiro recuo formal da doutrina que ele proprio enunciara em marco de 2025.", "inflation_conviction"),
   ("it's been five years, and we've actually had - we had the tariff shock, we had the pandemic, and now we have an energy shock of some size and duration.",
    "A contabilidade de choques em serie; e o argumento de que o padrao repetido, e nao cada choque isolado, ameaca as expectativas.", "inflation_conviction"),
   ("The policy that our - the possibility, rather, that our next move might be an increase did come up at the meeting, as it did at the last meeting.",
    "Confirma que a alta entrou na mesa por duas reunioes seguidas, ainda que nao como caso-base.", "near_term_bias"),
   ("we're a full percentage point above 2 percent for some time. And that's a concern.",
    "Sobre o nucleo em 3,0%; abandona a formula amenizadora 'somewhat elevated' das coletivas anteriores.", "mandate_weight")]},

{"key": "20260429", "comp": 2.5, "mand": 2.5, "infl": 4.0, "lab": 1.5, "stance": 2.0,
 "bias": ("hold", "patient"), "themes": ["tariffs", "ai_productivity", "fed_independence", "r_star"],
 "drivers": D(H(3), H(3), H(3), N(2), H(2), N(2)),
 "summary": "Ultima coletiva de Powell como presidente, e a mais hawkish do mandato dele no corpus. PCE cheio em 3,5% e nucleo em 3,2%, com o comunicado trocando 'somewhat elevated' por 'has moved up and is elevated'. Ele empilha as duas condicoes e fecha a porta do corte: quer ver o outro lado do choque de energia E o progresso prometido nas tarifas 'antes mesmo de pensarmos em reduzir juros'. Sobre o look-through de energia, diz que sera 'muito cauteloso', porque ja estao ha varios anos acima de 2% e ja estao olhando atraves do choque tarifario - dois look-throughs empilhados. Revela que TRES membros dissentiram, nao da decisao de juros, mas da LINGUAGEM: queriam ja migrar para um vies neutro em que 'a alta e tao provavel quanto o corte', e que esse grupo cresceu no periodo entre reunioes; ele mesmo reconhece que a mudanca 'concebivelmente pode vir ja na proxima reuniao'. Resume o desequilibrio numa frase: o emprego da sinais crescentes de estabilidade, 'enquanto a inflacao esta se comportando mal'. Postura corrente perto do neutro - ele nega que haja caso para chama-la de significativamente restritiva.",
 "quotes": [
   ("I think we'd want to see the back side of that and progress on tariffs before we even thought about, about reducing rates.",
    "Empilha as duas condicoes e retira o corte do horizonte proximo; e a frase que entrega o comite ja inclinado ao aperto ao sucessor.", "near_term_bias"),
   ("And I would say that the, you know, number of people on the Committee who either could support that language change changing to a more neutral stance so that the hike is as likely as a cut - that number has increased over the intermeeting period.",
    "Tres dissidencias sobre a LINGUAGEM, nao sobre a taxa; documenta a migracao do comite para um vies de duas maos antes mesmo da troca de comando.", "composite_hawk_dove"),
   ("The labor market shows more and more signs of stability, whereas inflation is kind of misbehaving.",
    "Sintese do desequilibrio entre os dois mandatos que justifica manter a restricao.", "mandate_weight"),
   ("I don't think there's much of a case for - any case, really - for, for policy looking, you know, meaningfully restrictive.",
    "Leitura da postura corrente; a mesma constatacao que Warsh converteria, seis semanas depois, em argumento para subir.", "policy_stance_read")]},
]


def main() -> None:
    for d in DOCS:
        key = d["key"]
        date = f"{key[:4]}-{key[4:6]}-{key[6:]}"
        sid = speech_id("powell", date, TITLE)
        rec = {
            "speech_id": sid, "member_id": "powell", "title": TITLE, "date": date,
            "url": URL.format(key=key), "source": "board", "non_policy": False,
            "summary": d["summary"],
            "key_quotes": [{"quote": q, "context": c, "dimension": dim}
                           for q, c, dim in d["quotes"]],
            "llm_scores": {
                "composite_hawk_dove": d["comp"], "mandate_weight": d["mand"],
                "inflation_conviction": d["infl"], "labor_concern": d["lab"],
                "policy_stance_read": d["stance"],
                "near_term_bias": {"direction": d["bias"][0], "pace": d["bias"][1]},
                "theme_flags": d["themes"]},
            "drivers": d["drivers"],
            "extractor_model": "claude-opus-5[1m]",
            "extracted_at": "2026-09-21T00:00:00Z",
            "rubric_version": "1.0",
        }
        raw = Path(config.SPEECHES_DIR) / f"{sid}.md"
        text = raw.read_text(encoding="utf-8")
        missing = [q for q, _, _ in d["quotes"] if q not in text]
        if missing:
            raise SystemExit(f"{sid}: citacao NAO verbatim -> {missing[0][:80]}")
        out = Path(config.EXTRACTED_DIR) / f"{sid}.json"
        out.write_text(json.dumps(rec, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {sid}  composite {d['comp']:+.1f}  (4 citacoes verbatim)")


if __name__ == "__main__":
    main()
