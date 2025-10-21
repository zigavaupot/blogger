# Graph & GraphRAG Demo


## Graphs – the bridge between data and generative artificial intelligence.

## Graphs – the bridge between data and generative artificial intelligence.

### Using Graphs as RAG in a GraphRAG scenario

In this workshop, we will setup a conversational agent that will enable to ask us questions about the well know children's book about a teddy bear called Piki Jakob written by Kajetan Kovič.

We will use property graph to capture relationships between persons and objects in a book and provide these relations to LLM in order to answer questions. Note that this is just a demonstraion of possible, however if you think it through, these kind of solution could improve the quality of narravive chat solutions.

Before we begin, I would also like to mention that this workshop has to pay all the credits to **Oracle LiveLabs** workshop **Gain a competitive edge with Generative AI, use AI to generate the Edge and Vertices that make Property Graph data structures** which I used as a reference

More about the referenced workshop: https://livelabs.oracle.com/pls/apex/r/dbpm/livelabs/view-workshop?wid=4174&clear=RR,180&session=14463983008299

In this workshop, we will setup a conversational agent that will enable to ask us questions about the well know children's book about a teddy bear called Piki Jakob written by Kajetan Kovič.

We will use property graph to capture relationships between persons and objects in a book and provide these relations to LLM in order to answer questions. Note that this is just a demonstraion of possible, however if you think it through, these kind of solution could improve the quality of narravive chat solutions.

Before we begin, I would also like to mention that this workshop has to pay all the credits to Oracle LiveLabs workshop Gain a competitive edge with Generative AI, use AI to generate the Edge and Vertices that make Property Graph data structures which I used as a reference

More about the referenced workshop: https://livelabs.oracle.com/pls/apex/r/dbpm/livelabs/view-workshop?wid=4174&clear=RR,180&session=14463983008299

During this workshop, one of the key tasks is to generate text outputs that will later be used for Retrieval-Augmented Generation (RAG).
We have prepared two configuration options for this step:

1.	**TinyBERT model** – a lightweight embedding model running directly inside the database.
2.	**OCI GenAI Llama model** – a large language model hosted on Oracle Cloud Infrastructure (later, we will also use Cohere for generating embeddings).

By default, the code uses OCI GenAI. To switch to TinyBERT, simply comment or uncomment the relevant section of the script.

During this workshop, one of the key tasks is to generate text outputs that will later be used for Retrieval-Augmented Generation (RAG).
We have prepared two configuration options for this step:

- TinyBERT model – a lightweight embedding model running directly inside the database.- OCI GenAI Llama model – a large language model hosted on Oracle Cloud Infrastructure (later, we will also use Cohere for generating embeddings).

By default, the code uses OCI GenAI. To switch to TinyBERT, simply comment or uncomment the relevant section of the script.

But before we begin, we need to verify few checks:

1. Does file "pravljice-MojPrijateljPikiJakob.txt" exists?
2. Is TinyBERT model available?

But before we begin, we need to verify few checks:

- Does file "pravljice-MojPrijateljPikiJakob.txt" exists?- Is TinyBERT model available?

```sql
CREATE OR REPLACE DIRECTORY GRAPHDIR as 'scratch/';
```

> Query executed successfully. Affected rows : 0

Checking if **pravljice-MojPrijateljPikiJakob.txt** exists in **GRAPHDIR** directory.

Checking if pravljice-MojPrijateljPikiJakob.txt exists in GRAPHDIR directory.

```sql
-- Checking if "pravljice-MojPrijateljPikiJakob.txt" exists in GRAPHDIR directory

DECLARE
  v_exists NUMBER := 0;
BEGIN
  -- Check if the file already exists in GRAPHDIR
  SELECT COUNT(*)
    INTO v_exists
    FROM TABLE(DBMS_CLOUD.LIST_FILES('GRAPHDIR')) t
   WHERE UPPER(t.object_name) = UPPER('pravljice-MojPrijateljPikiJakob.txt');

  -- If not found, download it from the specified location (and save with the exact file name)
  IF v_exists = 0 THEN
    DBMS_CLOUD.GET_OBJECT(
      object_uri     => 'https://objectstorage.eu-frankfurt-1.oraclecloud.com/n/frfoigjl2oaf/b/public-bucket/o/pravljice%2FMojPrijateljPikiJakob.txt',
      directory_name => 'GRAPHDIR',
      file_name      => 'pravljice-MojPrijateljPikiJakob.txt'
    );
    DBMS_OUTPUT.PUT_LINE('Downloaded: pravljice-MojPrijateljPikiJakob.txt');
  ELSE
    DBMS_OUTPUT.PUT_LINE('File already present: pravljice-MojPrijateljPikiJakob.txt');
  END IF;
END;
```

> File already present: pravljice-MojPrijateljPikiJakob.txt
> 
> PL/SQL procedure successfully completed.

Checking if **TinyBERT** model exists in database ...

Checking if TinyBERT model exists in database ...

```sql
DECLARE
  v_model_exists NUMBER := 0;
  v_file_exists  NUMBER := 0;
BEGIN
  ---------------------------------------------------------------------------
  -- 1) Check if the ONNX model is already loaded (use Data Mining catalog)
  ---------------------------------------------------------------------------
  BEGIN
    SELECT COUNT(*)
      INTO v_model_exists
      FROM USER_MINING_MODELS
     WHERE UPPER(model_name) = 'TINYBERT_MODEL';
  EXCEPTION
    WHEN OTHERS THEN
      -- If the view isn't available for some reason, assume not present
      v_model_exists := 0;
  END;

  IF v_model_exists = 1 THEN
    DBMS_OUTPUT.PUT_LINE('Model TINYBERT_MODEL already loaded. Skipping load.');
    RETURN;
  END IF;

  DBMS_OUTPUT.PUT_LINE('Model TINYBERT_MODEL not found. Checking GRAPHDIR...');

  ---------------------------------------------------------------------------
  -- 2) Check if tinybert.onnx exists in GRAPHDIR; if not, download it
  ---------------------------------------------------------------------------
  SELECT COUNT(*)
    INTO v_file_exists
    FROM TABLE(DBMS_CLOUD.LIST_FILES('GRAPHDIR')) t
   WHERE UPPER(t.object_name) = 'TINYBERT.ONNX';

  IF v_file_exists = 0 THEN
    DBMS_OUTPUT.PUT_LINE('tinybert.onnx not found. Downloading...');
    DBMS_CLOUD.GET_OBJECT(
      object_uri     => 'https://objectstorage.us-chicago-1.oraclecloud.com/n/idb6enfdcxbl/b/Livelabs/o/onnx-embedding-models/tinybert.onnx',
      directory_name => 'GRAPHDIR',
      file_name      => 'tinybert.onnx'
    );
  ELSE
    DBMS_OUTPUT.PUT_LINE('tinybert.onnx already exists in GRAPHDIR.');
  END IF;

  ---------------------------------------------------------------------------
  -- 3) Load ONNX model into schema (catch ORA-40204 just in case)
  ---------------------------------------------------------------------------
  DBMS_OUTPUT.PUT_LINE('Loading ONNX model into schema as TINYBERT_MODEL...');
  BEGIN
    DBMS_VECTOR.LOAD_ONNX_MODEL(
      directory  => 'GRAPHDIR',
      file_name  => 'tinybert.onnx',
      model_name => 'TINYBERT_MODEL',
      metadata   => JSON('{
        "function":"embedding",
        "embeddingOutput":"embedding",
        "input":{"input":["DATA"]}
      }')
    );
    DBMS_OUTPUT.PUT_LINE('TINYBERT_MODEL successfully loaded.');
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE = -40204 THEN
        -- ORA-40204: model already exists
        DBMS_OUTPUT.PUT_LINE('TINYBERT_MODEL already exists. Skipping load.');
      ELSE
        RAISE;
      END IF;
  END;
END;
```

> Model TINYBERT_MODEL already loaded. Skipping load.
> 
> PL/SQL procedure successfully completed.

Setting profiles for selected model ...

Setting profiles for selected model ...

```sql
DECLARE
  -- Switch: set to 'TinyBERT' or 'OCI GenAI'
  selected_model VARCHAR2(20) := 'OCI GenAI';
BEGIN
  -- Drop if present (ignore if not)
  DBMS_CLOUD_AI.DROP_PROFILE(
    profile_name => 'GRAPHUSER_PROFILE',
    force        => TRUE   -- avoids ORA-20046 if profile doesn't exist
  );

  -- Create the profile based on the selected model
  IF selected_model = 'TinyBERT' THEN
    DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => 'GRAPHUSER_PROFILE',
      attributes   => '{
        "provider": "database",
        "embedding_model": "tinybert_model"
      }'
    );

  ELSIF selected_model = 'OCI GenAI' THEN
    DBMS_CLOUD_AI.CREATE_PROFILE(
      profile_name => 'GRAPHUSER_PROFILE',
      attributes   => '{
        "provider": "oci",
        "region": "eu-frankfurt-1",
        "credential_name": "GENAI_GRAPH_CREDENTIAL",
        "conversation": "true",
        "model": "meta.llama-3.3-70b-instruct"
      }'
    );

  ELSE
    RAISE_APPLICATION_ERROR(-20001,
      'Invalid selected_model. Use "TinyBERT" or "OCI GenAI".');
  END IF;

  -- Activate for the session
  DBMS_CLOUD_AI.SET_PROFILE(profile_name => 'GRAPHUSER_PROFILE');

  DBMS_OUTPUT.PUT_LINE(
    'GRAPHUSER_PROFILE created and activated with model: ' || selected_model);
END;
/
```

> GRAPHUSER_PROFILE created and activated with model: OCI GenAI
> 
> PL/SQL procedure successfully completed.

In the next paragraph, story is read into tables. First, we will read it into a BLOB which is then converted into CLOB which is suitable for further processing.

In the next paragraph, story is read into tables. First, we will read it into a BLOB which is then converted into CLOB which is suitable for further processing.

```sql
BEGIN
  ---------------------------------------------------------------------------
  -- Drop and recreate STORY_TABLE_BLOB
  -- This table stores binary (BLOB) content such as original uploaded files.
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE STORY_TABLE_BLOB PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      -- Ignore "table or view does not exist" (ORA-00942) so script is reusable
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF;
  END;

  EXECUTE IMMEDIATE 'CREATE TABLE STORY_TABLE_BLOB (
    ID   NUMBER,   -- document identifier
    DATA BLOB      -- binary large object (original file content)
  )';

  ---------------------------------------------------------------------------
  -- Drop and recreate STORY_TABLE_CLOB
  -- This table stores textual (CLOB) content extracted from BLOBs.
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE STORY_TABLE_CLOB PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF;
  END;

  EXECUTE IMMEDIATE 'CREATE TABLE STORY_TABLE_CLOB (
    ID   NUMBER,   -- document identifier (matches STORY_TABLE_BLOB)
    DATA CLOB      -- text content extracted from the BLOB
  )';

  ---------------------------------------------------------------------------
  -- Drop and recreate STORY_TABLE_CHUNKS
  -- This table stores sentence-level text chunks and their vector embeddings.
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE STORY_TABLE_CHUNKS PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF;
  END;

  EXECUTE IMMEDIATE 'CREATE TABLE STORY_TABLE_CHUNKS (
    DOC_ID         NUMBER,          -- reference to document in STORY_TABLE_CLOB
    CHUNK_ID       NUMBER,          -- sequential chunk identifier
    CHUNK_DATA     VARCHAR2(4000),  -- individual sentence or text segment
    CHUNK_EMBEDDING VECTOR          -- vector embedding for semantic search
  )';
END;
/
```

> PL/SQL procedure successfully completed.

```sql
-- Insert the story text file into STORY_TABLE_BLOB as a BLOB
-- Reads the file 'pravljice-MojPrijateljPikiJakob.txt' from the Oracle directory GRAPHDIR.
BEGIN
    INSERT INTO STORY_TABLE_BLOB
    VALUES (
        1,
        TO_BLOB(
            BFILENAME('GRAPHDIR', 'pravljice-MojPrijateljPikiJakob.txt')
        )
    );
    COMMIT;
-- Optional: view the inserted row
-- SELECT * FROM STORY_TABLE_BLOB;
END;
/

BEGIN
-- Convert the BLOB into a CLOB (character large object)
-- This makes the story text readable and usable for NLP and embedding generation.
    INSERT INTO STORY_TABLE_CLOB
    SELECT ID, TO_CLOB(DATA)
    FROM STORY_TABLE_BLOB;

-- Optional: view the converted text
-- SELECT * FROM STORY_TABLE_CLOB;
    COMMIT;
END;
/
```

> PL/SQL procedure successfully completed.
> 
> PL/SQL procedure successfully completed.

The next paragpraph, code builds a semantic embedding dataset from story text stored in Oracle database table.
It takes the story text from STORY_TABLE_CLOB, splits it into sentence-level chunks, and generates an embedding vector for each chunk — a numeric representation of meaning used for similarity search or AI applications.
Two alternative embedding methods are provided:

1.	**Local (database) embedding** using Oracle’s built-in **TinyBERT model**, which runs directly inside the database.
2.	**Cloud-based embedding** using **OCI Generative AI** with the **Cohere Multilingual v3.0 model**, which calls Oracle Cloud’s external GenAI service through stored credentials.

Only one method should be used at a time — the other remains commented out. Both produce the same output structure in STORY_TABLE_CHUNKS: document ID, chunk ID, text content, and its corresponding embedding vector.

Both methods ulitmately populata **STORY_TABLE_CHUNKS** with sentences and their embeddings, ready for vector search or RAG use cases.

The next paragpraph, code builds a semantic embedding dataset from story text stored in Oracle database table.
It takes the story text from STORY_TABLE_CLOB, splits it into sentence-level chunks, and generates an embedding vector for each chunk — a numeric representation of meaning used for similarity search or AI applications.
Two alternative embedding methods are provided:

- Local (database) embedding using Oracle’s built-in TinyBERT model, which runs directly inside the database.- Cloud-based embedding using OCI Generative AI with the Cohere Multilingual v3.0 model, which calls Oracle Cloud’s external GenAI service through stored credentials.

Only one method should be used at a time — the other remains commented out. Both produce the same output structure in STORY_TABLE_CHUNKS: document ID, chunk ID, text content, and its corresponding embedding vector.

Both methods ulitmately populata STORY_TABLE_CHUNKS with sentences and their embeddings, ready for vector search or RAG use cases.

```sql
DECLARE
  -- Switch: 'TinyBERT' or 'OCI GenAI'
  selected_model VARCHAR2(20) := 'OCI GenAI';
  v_config   CLOB;
BEGIN
  -- Choose embedding configuration based on selected_model
  IF selected_model = 'TinyBERT' THEN
    v_config := '{"provider":"database","model":"tinybert_model"}';
  ELSIF selected_model = 'OCI GenAI' THEN
    v_config := '{
      "provider": "ocigenai",
      "credential_name": "OCI_GENAI_CRED_GRAPH",
      "url": "https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/20231130/actions/embedText",
      "model": "cohere.embed-multilingual-v3.0"
    }';
  ELSE
    RAISE_APPLICATION_ERROR(-20001, 'Invalid selected_model. Use "TinyBERT" or "OCI GenAI".');
  END IF;

  -- Insert embeddings
  INSERT INTO STORY_TABLE_CHUNKS
  SELECT
      DT.ID                        AS DOC_ID,
      ET.EMBED_ID                  AS CHUNK_ID,
      ET.EMBED_DATA                AS CHUNK_DATA,
      TO_VECTOR(ET.EMBED_VECTOR)   AS CHUNK_EMBEDDING
  FROM
      STORY_TABLE_CLOB DT,
      TABLE(
        DBMS_VECTOR_CHAIN.UTL_TO_EMBEDDINGS(
          -- split & normalize into sentence chunks
          DBMS_VECTOR_CHAIN.UTL_TO_CHUNKS(
            DBMS_VECTOR_CHAIN.UTL_TO_TEXT(DT.DATA),
            JSON('{"split":"sentence","normalize":"all"}')
          ),
          -- pass SQL JSON, not PL/SQL JSON object
          JSON(v_config)
        )
      ) T,
      JSON_TABLE(
        T.COLUMN_VALUE, '$[*]'
        COLUMNS (
          EMBED_ID      NUMBER           PATH '$.embed_id',
          EMBED_DATA    VARCHAR2(4000)   PATH '$.embed_data',
          EMBED_VECTOR  CLOB             PATH '$.embed_vector'
        )
      ) ET;

  COMMIT;

  DBMS_OUTPUT.PUT_LINE('Embeddings generated using model: ' || selected_model);
END;
```

> Embeddings generated using model: OCI GenAI
> 
> PL/SQL procedure successfully completed.

Let's review what have we done so far ... **STORY_TABLE_CHUNKS** includes our story split into chunks. 
The query below simply displays the first 20 text chunks (their document ID, chunk ID, and text) from the chunks table. It isuseful for quickly previewing what kind of data has been loaded or chunked before generating embeddings or running similarity searches.

Let's review what have we done so far ... STORY_TABLE_CHUNKS includes our story split into chunks.
The query below simply displays the first 20 text chunks (their document ID, chunk ID, and text) from the chunks table. It isuseful for quickly previewing what kind of data has been loaded or chunked before generating embeddings or running similarity searches.

```sql
SELECT doc_id, chunk_id, chunk_data
FROM STORY_TABLE_CHUNKS
FETCH FIRST 20 ROWS ONLY;
```

> DOC_ID	CHUNK_ID	CHUNK_DATA
> 1	31	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 1	32	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 1	33	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 1	34	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 1	35	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 1	36	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 1	37	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 1	38	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 1	39	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 1	40	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 1	41	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 1	42	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 1	43	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 1	44	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 1	45	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 1	46	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 1	47	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 1	48	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 1	49	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 1	50	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.

```sql
SELECT count(*)
FROM STORY_TABLE_CHUNKS
```

> COUNT(*)
> 148

**extract_graph** — as its name suggests — extracts graph data directly from a given text.  

* First, a precise **prompt (in Slovene)** is constructed. It instructs the LLM to act as a *knowledge-graph extractor* and to return **only a JSON array** of objects containing the fields: `head`, `head_type`, `relation`, `tail`, `tail_type`, and `data_chunk`. The prompt also enforces naming and normalization rules and provides concise format examples.  
* Next, **OCI GenAI** is invoked via `DBMS_CLOUD_AI.GENERATE`, using the **GRAPHUSER_PROFILE** profile (with the `chat` action). Depending on the configuration at the top of the notebook, this may use either **OCI GenAI** or **TinyBERT** to process the provided `text_chunk`.  
* The response is then **cleaned and normalized**:
  * Leading and trailing whitespace is trimmed.  
  * If the model returns a single JSON object (`{...}`) instead of an array, it is wrapped as `[ {...} ]`.  
* The output is **validated as JSON**. The function attempts to parse it as a `JSON_ARRAY_T`; if parsing fails, an empty array string (`[]`) is safely returned.  
* Finally, the function returns a **CLOB** containing a valid JSON array of extracted triples — or `[]` if no valid data is found.

```sql
CREATE OR REPLACE FUNCTION extract_graph (text_chunk CLOB)
  RETURN CLOB
IS
  l_prompt   CLOB;
  l_response CLOB;
BEGIN
  l_prompt := q'~
  Ti si ekstraktor za grafe znanja. Iz podanega besedila izlušči entitete in relacije ter vrni LE JSON tabelo (array) objektov brez dodatnega besedila, kode blokov ali razlag.

  IZHODNA SHEMA (za vsak objekt v tabeli):
  {
    "head": string,        -- čitljiv, unikaten identifikator glavne entitete (npr. "Piki Jakob", "učitelj")
    "head_type": string,   -- tip glavne entitete (npr. "oseba", "izdelek", "podjetje", "prostor", "igra", "značilnost", "nagrada", "predmet")
    "relation": string,    -- relacija med entitetama (npr. "živi", "igra", "vozi", "se pogovarja", "ima lastnost", "proizvaja", "dela za", "ima nagrado")
    "tail": string,        -- čitljiv, unikaten identifikator povezane entitete, enaka pravila kot za "head"
    "tail_type": string,   -- tip povezane entitete, enaka pravila kot za "head_type"
    "data_chunk": string   -- dobesedni odsek iz vhoda, ki podpira relacijo
  }

  PRAVILA:
  - Vrni samo VELJAVEN JSON array (brez uvoda/razlage/kode blokov).
  - Uporabi najpopolnejša imena entitet (npr. “Piki Jakob”, ne “Jakob” ali “Piki”).
  - Vsa poimenovanja v malih črkah, razen osebnih imen (ime in priimek z veliko začetnico).
  - Normaliziraj sklanjatve/okrajšave na osnovno poimenovanje.
  - Brez podvajanja: združi enake (head, relation, tail).
  - Če ni ustreznega »tail«, vrni prazen array: [].
  - »head« in »tail« ne smeta biti ista entiteta v isti relaciji.
  - V »data_chunk« vključi kratek dobesedni izsek vhoda, ki upravičuje trojico.

  KRATKI PRIMERI (format, ne vsebina):
  [
  {"head":"Piki Jakob","head_type":"oseba","relation":"živi","tail":"blok","tail_type":"prostor","data_chunk":"Piki Jakob živi v bloku."},
  {"head":"Piki Jakob","head_type":"oseba","relation":"igra","tail":"šah","tail_type":"igra","data_chunk":"rad igra šah."},
  {"head":"Microsoft Word","head_type":"izdelek","relation":"proizvaja","tail":"Microsoft","tail_type":"podjetje","data_chunk":"Microsoft Word je izdelek Microsofta."},
  {"head":"Adam","head_type":"oseba","relation":"dela za","tail":"Oracle","tail_type":"podjetje","data_chunk":"Adam dela za Oracle."},
  {"head":"Adam","head_type":"oseba","relation":"ima nagrado","tail":"Najboljši talent","tail_type":"nagrada","data_chunk":"prejel je nagrado Najboljši talent."},
  {"head":"Microsoft Word","head_type":"izdelek","relation":"ima lastnost","tail":"lahka aplikacija","tail_type":"značilnost","data_chunk":"je lahka aplikacija."},
  {"head":"Microsoft Word","head_type":"izdelek","relation":"ima lastnost","tail":"dostopna brez povezave","tail_type":"značilnost","data_chunk":"dostopna je brez povezave."}
  ]

  VHODNO BESEDILO:
  ~' || text_chunk;

  l_response := DBMS_CLOUD_AI.GENERATE(
    prompt       => l_prompt,
    profile_name => 'GENAI_GRAPH_PROFILE_OCI',
    action       => 'chat'
  );

  -- Počisti presledke
  l_response := REGEXP_REPLACE(l_response, '^\s+|\s+$', '');

  -- Če je vrnjen objekt namesto tabele, ga ovij v tabelo
  IF SUBSTR(l_response, 1, 1) = '{' THEN
    l_response := '[' || l_response || ']';
  END IF;

  -- Validacija JSON array; ob napaki vrni []
  DECLARE
    v_arr JSON_ARRAY_T;
  BEGIN
    v_arr := JSON_ARRAY_T.parse(l_response);
  EXCEPTION
    WHEN OTHERS THEN
      l_response := '[]';
  END;

  RETURN l_response;
END;
/
```

> Function EXTRACT_GRAPH compiled

The next script clears and recreates a staging table for storing AI-extracted knowledge graph data per chunk — each record links a text chunk (CHUNK_ID) to its extracted JSON graph output (RESPONSE).

The next script clears and recreates a staging table for storing AI-extracted knowledge graph data per chunk — each record links a text chunk (CHUNK_ID) to its extracted JSON graph output (RESPONSE).

```sql
BEGIN
---------------------------------------------------------------------------
  -- Drop and recreate GRAPH_EXTRACTION_STAGING
  -- This table stores sentence-level text chunks and their vector embeddings.
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE GRAPH_EXTRACTION_STAGING PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF;
  END;

  EXECUTE IMMEDIATE 'CREATE TABLE GRAPH_EXTRACTION_STAGING (
    CHUNK_ID    NUMBER,
    RESPONSE    CLOB
  )';
END;
```

> PL/SQL procedure successfully completed.

Here’s a concise summary of what LOAD_EXTRACT_TABLE (see the next paragraph) does:
* Sets the active AI profile to GRAPHUSER_PROFILE for downstream LLM calls.
* Finds up to 1,000 unprocessed text chunks in STORY_TABLE_CHUNKS (those whose chunk_id isn’t present in GRAPH_EXTRACTION_STAGING), ordered by chunk_id.
* Iterates through those chunks and, for each one:
* Calls extract_graph(chunk_data) to get a JSON array of extracted triples.
* Inserts (chunk_id, response) into GRAPH_EXTRACTION_STAGING.
* Limits each run to ~10 chunks (technically 11 due to x := x + 1 before EXIT WHEN x > 10).

Here’s a concise summary of what LOAD_EXTRACT_TABLE (see the next paragraph) does:- Sets the active AI profile to GRAPHUSER_PROFILE for downstream LLM calls.- Finds up to 1,000 unprocessed text chunks in STORY_TABLE_CHUNKS (those whose chunk_id isn’t present in GRAPH_EXTRACTION_STAGING), ordered by chunk_id.- Iterates through those chunks and, for each one:- Calls extract_graph(chunk_data) to get a JSON array of extracted triples.- Inserts (chunk_id, response) into GRAPH_EXTRACTION_STAGING.- Limits each run to ~10 chunks (technically 11 due to x := x + 1 before EXIT WHEN x > 10).

```sql
CREATE OR REPLACE PROCEDURE LOAD_EXTRACT_TABLE 
AS
BEGIN
  -- Declare a counter to limit the number of chunks processed per run
  DECLARE
      x NUMBER := 0;
  BEGIN

      DBMS_CLOUD_AI.SET_PROFILE('GRAPHUSER_PROFILE');

      -- Loop through text chunks that have NOT yet been added to the staging table
      -- Only consider chunks with CHUNK_ID between 1 and 1000
      -- Order by CHUNK_ID to process them sequentially
      FOR text_chunk IN (
          SELECT c.chunk_id, c.chunk_data 
          FROM  STORY_TABLE_CHUNKS c 
               LEFT JOIN GRAPH_EXTRACTION_STAGING s 
               ON s.chunk_id = c.chunk_id
          WHERE s.chunk_id IS NULL              -- select only missing (unprocessed) chunks
            AND c.chunk_id > 0 
            AND c.chunk_id <= 1000
          ORDER BY c.chunk_id
      )
      LOOP
          -- Increment the counter
          x := x + 1;

          -- Call the extract_graph() function for each chunk
          -- and insert the AI-generated response into the staging table
          INSERT INTO GRAPH_EXTRACTION_STAGING (chunk_id, response)
          SELECT text_chunk.chunk_id,
                 extract_graph(text_chunk.chunk_data) AS response
          FROM dual;

          -- Stop the loop after processing 10 (actually 11 due to check order)
          EXIT WHEN x > 10;
      END LOOP;

  END;
END;
/
```

> Procedure LOAD_EXTRACT_TABLE compiled

This code completely resets and recreates an automated database job that periodically runs the stored procedure **LOAD_EXTRACT_TABLE**.

First, it removes all existing scheduler jobs owned by the current user to ensure a clean slate. Then, it creates a new job named **runExtractStagingStoredProcedure** that executes the **LOAD_EXTRACT_TABLE** procedure. Next, it configures the **job’s schedule** — setting the start time to the current moment, the end time to one hour later, and defining a repeat interval of **every 2 minutes**. Finally, the job is enabled, causing Oracle’s scheduler to automatically **invoke LOAD_EXTRACT_TABLE every two minutes** for the next hour.

**IMPORTANT**:

Run this step only if you need to recreate the **GRAPH_EXTRACTION_STAGING** table.
The process takes approximately **30 minutes** to complete.
If the table already exists, you **may prefer to skip** this step and continue with the most recent extraction results instead.

If you decide to skip, then move forward to the paragraph **TEST EMBEDDINGS**.

This code completely resets and recreates an automated database job that periodically runs the stored procedure LOAD_EXTRACT_TABLE.

First, it removes all existing scheduler jobs owned by the current user to ensure a clean slate. Then, it creates a new job named runExtractStagingStoredProcedure that executes the LOAD_EXTRACT_TABLE procedure. Next, it configures the job’s schedule — setting the start time to the current moment, the end time to one hour later, and defining a repeat interval of every 2 minutes. Finally, the job is enabled, causing Oracle’s scheduler to automatically invoke LOAD_EXTRACT_TABLE every two minutes for the next hour.

IMPORTANT:

Run this step only if you need to recreate the GRAPH_EXTRACTION_STAGING table.
The process takes approximately 30 minutes to complete.
If the table already exists, you may prefer to skip this step and continue with the most recent extraction results instead.

If you decide to skip, then move forward to the paragraph TEST EMBEDDINGS.

```sql
BEGIN
  FOR j IN (SELECT job_name FROM user_scheduler_jobs) LOOP
    DBMS_SCHEDULER.DROP_JOB(job_name => j.job_name, force => TRUE);
  END LOOP;
END;
/

BEGIN
    SYS.DBMS_SCHEDULER.CREATE_JOB ( 
            job_name => 'runExtractStagingStoredProcedure',
            job_type => 'STORED_PROCEDURE',
            job_action => 'LOAD_EXTRACT_TABLE'
        ); 
END;
/

DECLARE 
    Startjob TIMESTAMP;
    endjob TIMESTAMP;
BEGIN 
    Startjob := CURRENT_TIMESTAMP;
    endjob := Startjob + 1/24;

    SYS.DBMS_SCHEDULER.SET_ATTRIBUTE( 
            name => 'runExtractStagingStoredProcedure',
            attribute => 'START_DATE',
            value => Startjob
        );
    SYS.DBMS_SCHEDULER.SET_ATTRIBUTE( 
            name => 'runExtractStagingStoredProcedure',
            attribute => 'REPEAT_INTERVAL',
            value => 'FREQ=MINUTELY; INTERVAL=2'
        );
    SYS.DBMS_SCHEDULER.SET_ATTRIBUTE( 
            name => 'runExtractStagingStoredProcedure',
            attribute => 'END_DATE',
            value => endjob
        );

    SYS.DBMS_SCHEDULER.enable(name => 'runExtractStagingStoredProcedure'); 
END;
/
```

> PL/SQL procedure successfully completed.
> 
> PL/SQL procedure successfully completed.
> 
> PL/SQL procedure successfully completed.

The following set of SQL queries is used to monitor and troubleshoot Oracle Scheduler jobs.
* The first query lists all jobs defined in the current schema (user_scheduler_jobs) and shows whether they’re enabled, their current state, and when they last and next ran.
* The second query checks for jobs that are currently running, displaying their session ID, instance, elapsed time, and CPU usage.
* The third query retrieves the execution history of all jobs from user_scheduler_job_run_details, including status, timestamps, run durations, and any additional information, ordered by most recent first.

**Important*: Run each of these SQL statements separately — one at a time — while commenting out the other two. Graph Studio (and most Oracle tools) executes only one SQL statement per paragraph or cell, so separating them ensures each query runs correctly and displays its own results.

The following set of SQL queries is used to monitor and troubleshoot Oracle Scheduler jobs.- The first query lists all jobs defined in the current schema (user_scheduler_jobs) and shows whether they’re enabled, their current state, and when they last and next ran.- The second query checks for jobs that are currently running, displaying their session ID, instance, elapsed time, and CPU usage.- The third query retrieves the execution history of all jobs from user_scheduler_job_run_details, including status, timestamps, run durations, and any additional information, ordered by most recent first.
*Important: Run each of these SQL statements separately — one at a time — while commenting out the other two. Graph Studio (and most Oracle tools) executes only one SQL statement per paragraph or cell, so separating them ensures each query runs correctly and displays its own results.

```sql
/* SELECT job_name,
       enabled,
       state,
       last_start_date,
       next_run_date
FROM user_scheduler_jobs; */

/* SELECT job_name,
       session_id,
       running_instance,
       elapsed_time,
       cpu_used
FROM user_scheduler_running_jobs; */

SELECT job_name,
       status,
       log_date,
       run_duration,
       additional_info
FROM user_scheduler_job_run_details
ORDER BY log_date DESC;
```

> JOB_NAME	STATUS	LOG_DATE	RUN_DURATION	ADDITIONAL_INFO
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:39:08.871508 +0:00	0 0:1:11.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:36:08.043733 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:34:08.115593 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:32:08.102276 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:30:08.17257 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:28:08.17182 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:26:08.068841 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:24:08.079611 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:24:01.005536 +0:00	0 0:0:59.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:23:01.557582 +0:00	0 0:2:24.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:20:37.203568 +0:00	0 0:1:55.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:18:42.382121 +0:00	0 0:2:16.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:16:26.627149 +0:00	0 0:1:41.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:14:45.282157 +0:00	0 0:2:17.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:12:28.55708 +0:00	0 0:2:20.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:10:08.189247 +0:00	0 0:1:55.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:08:13.45685 +0:00	0 0:2:41.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:05:32.433692 +0:00	0 0:2:3.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:03:29.821835 +0:00	0 0:2:33.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 17:00:56.553382 +0:00	0 0:2:40.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 16:58:16.810981 +0:00	0 0:2:8.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 16:56:05.275039 +0:00	0 0:1:57.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:55:58.616195 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:53:58.035797 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:51:58.04108 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:49:58.208959 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:47:58.224435 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:45:58.229296 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:43:58.210236 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:41:58.183193 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:39:58.14461 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:37:58.229696 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:35:58.070735 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:33:58.113033 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:31:58.030928 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:29:58.074995 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:27:58.077142 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:25:58.177773 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:24:34.185013 +0:00	0 0:0:36.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:23:24.936295 +0:00	0 0:1:27.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:21:10.633022 +0:00	0 0:1:12.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:18:59.131262 +0:00	0 0:1:1.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:17:37.414168 +0:00	0 0:1:39.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:15:23.347771 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:13:43.934402 +0:00	0 0:1:46.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:11:10.741957 +0:00	0 0:1:13.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:09:22.861869 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:07:12.499724 +0:00	0 0:1:14.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:05:13.487319 +0:00	0 0:1:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:03:11.279639 +0:00	0 0:1:13.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 13:01:23.108287 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 12:59:16.763266 +0:00	0 0:1:19.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 09:27:22.217857 +0:00	0 0:1:5.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 09:25:51.233254 +0:00	0 0:1:33.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-12 09:23:41.425136 +0:00	0 0:1:23.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:40:26.195224 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:38:26.13252 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:36:26.070855 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:34:26.063912 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:32:26.106032 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:30:26.060544 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:28:26.128529 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:26:26.193735 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:24:26.190129 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:22:26.200718 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:20:26.217035 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:18:26.20705 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:16:26.03272 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:14:26.067407 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:12:26.089417 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:10:26.20913 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:08:59.112266 +0:00	0 0:0:33.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:07:54.994167 +0:00	0 0:1:29.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:05:41.586368 +0:00	0 0:1:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:03:29.145311 +0:00	0 0:1:3.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 13:02:04.730365 +0:00	0 0:1:39.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:59:50.383329 +0:00	0 0:1:24.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:58:05.891883 +0:00	0 0:1:40.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:55:41.48833 +0:00	0 0:1:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:53:50.691644 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:51:52.989093 +0:00	0 0:1:27.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:49:37.17623 +0:00	0 0:1:11.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:47:39.161488 +0:00	0 0:1:13.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:45:53.523319 +0:00	0 0:1:26.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:43:46.501564 +0:00	0 0:1:20.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-10-11 12:41:08.518182 +0:00	0 0:1:14.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:37:50.57341 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:35:50.553381 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:34:57.145609 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:32:57.088294 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:29:28.957157 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-10-11 12:26:13.058854 +0:00	0 0:0:0.0	ORA-20046: AI profile is not enabled in the session ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD$PDBCS_250919_0", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 18252 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 44 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 28 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:47:53.174842 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:45:53.137532 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:43:53.151399 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:41:53.147597 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:39:53.105371 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:37:53.12149 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:35:53.179183 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:33:53.098252 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:31:53.097938 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:29:53.057365 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:27:53.105205 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:25:53.196372 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:23:53.030495 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:21:53.213461 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:20:26.95328 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:20:26.93184 +0:00	0 0:0:44.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:19:42.771398 +0:00	0 0:2:18.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:17:24.523329 +0:00	0 0:2:10.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:15:14.12423 +0:00	0 0:1:57.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:13:17.27987 +0:00	0 0:2:9.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:11:08.276213 +0:00	0 0:2:14.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:08:53.938104 +0:00	0 0:2:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:06:25.678519 +0:00	0 0:2:18.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:04:08.075165 +0:00	0 0:2:33.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 15:01:35.243775 +0:00	0 0:2:43.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:58:52.00593 +0:00	0 0:2:14.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:56:38.460247 +0:00	0 0:1:50.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:54:48.818749 +0:00	0 0:2:47.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:52:01.764068 +0:00	0 0:2:9.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	STOPPED	2025-09-19 14:49:50.00331 +0:00	0 0:0:25.0	REASON="Stop job called by user: 'GRAPHUSER'"
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:47:25.096368 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:45:25.057753 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:43:25.154463 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:41:25.173237 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:39:25.211692 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:37:25.023281 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:35:25.174958 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:33:25.159778 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:31:25.193122 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:29:25.058284 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:27:59.869375 +0:00	0 0:0:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:26:55.562556 +0:00	0 0:1:31.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:25:04.690194 +0:00	0 0:1:39.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:23:05.329539 +0:00	0 0:1:40.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:21:00.4603 +0:00	0 0:1:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:19:02.035687 +0:00	0 0:1:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:17:26.926555 +0:00	0 0:2:2.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:14:50.53244 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:12:53.314415 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:10:47.282609 +0:00	0 0:1:22.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:08:50.376899 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:06:54.111937 +0:00	0 0:1:29.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:05:02.760436 +0:00	0 0:1:37.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 14:02:51.450763 +0:00	0 0:1:26.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 13:54:55.065163 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-19 13:52:55.062362 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:50:49.998114 +0:00	0 0:0:0.0	ORA-20000: AI profile with provider database can only be used for vector embeddings. ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:49:44.127482 +0:00	0 0:0:0.0	ORA-20000: AI profile with provider database can only be used for vector embeddings. ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:47:44.129305 +0:00	0 0:0:0.0	ORA-20046: Profile GENAI_GRAPH_PROFILE_TINYBERT does not exist. ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:45:44.394901 +0:00	0 0:0:0.0	ORA-20404: Object not found - https://inference.generativeai.eu-frankfurt-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:43:45.241668 +0:00	0 0:0:0.0	ORA-20404: Object not found - https://inference.generativeai.eu-frankfurt-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:41:45.25547 +0:00	0 0:0:0.0	ORA-20404: Object not found - https://inference.generativeai.eu-frankfurt-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-19 13:40:26.171802 +0:00	0 0:0:0.0	ORA-20404: Object not found - https://inference.generativeai.eu-frankfurt-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:12:01.104282 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:10:01.037507 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:08:01.219913 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:06:01.051393 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:04:01.036614 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:02:01.091398 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 16:00:01.11191 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:58:01.069574 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:56:01.152199 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:54:01.219921 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:52:01.052025 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:50:01.0601 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:48:01.133752 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:46:01.113031 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:44:01.060131 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:42:01.0181 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:40:01.216088 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:38:01.213925 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:36:01.043408 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:34:01.23289 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:32:01.045262 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:30:01.038012 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:28:01.196523 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:26:01.029325 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:24:01.05251 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:22:01.18292 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:20:01.037575 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:18:01.035302 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-14 15:16:02.11678 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:12:54.046372 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:10:54.038999 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:09:27.914644 +0:00	0 0:0:34.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:08:23.785136 +0:00	0 0:1:30.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:06:34.976525 +0:00	0 0:1:41.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:04:28.145862 +0:00	0 0:1:34.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:02:28.752309 +0:00	0 0:1:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 15:00:21.876559 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:58:43.76339 +0:00	0 0:1:50.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:56:22.422213 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:54:22.477441 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:52:29.254113 +0:00	0 0:1:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:50:16.819007 +0:00	0 0:1:23.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:48:26.158393 +0:00	0 0:1:32.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:46:31.912457 +0:00	0 0:1:37.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:44:16.100926 +0:00	0 0:1:24.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:40:52.052263 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:38:52.113725 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:36:52.072298 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:34:52.070003 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:32:52.07107 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:31:30.10515 +0:00	0 0:0:38.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:30:04.712314 +0:00	0 0:1:13.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:28:09.580076 +0:00	0 0:1:18.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:26:27.291767 +0:00	0 0:1:35.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:23:57.417238 +0:00	0 0:1:5.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:22:11.511357 +0:00	0 0:1:19.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:20:39.815688 +0:00	0 0:1:48.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:18:13.776581 +0:00	0 0:1:22.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:16:02.588542 +0:00	0 0:1:10.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:13:56.376462 +0:00	0 0:1:4.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:12:10.005078 +0:00	0 0:1:18.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:10:06.739617 +0:00	0 0:1:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:08:19.155673 +0:00	0 0:1:27.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 14:06:08.795321 +0:00	0 0:1:16.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:27:18.16962 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:25:18.195091 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:23:18.183015 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:21:18.313245 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:19:18.144618 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:17:18.135905 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:15:18.10691 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:13:18.086875 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:11:18.090396 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:09:18.043681 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:07:18.171289 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:05:18.22212 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:03:18.173729 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 13:01:18.06001 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:59:18.183313 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:57:18.026681 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:55:56.297298 +0:00	0 0:0:38.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:54:30.843854 +0:00	0 0:1:13.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:52:46.405514 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:50:52.374051 +0:00	0 0:1:34.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:48:33.896499 +0:00	0 0:1:16.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:46:36.363049 +0:00	0 0:1:18.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:44:58.948041 +0:00	0 0:1:41.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:42:43.225371 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:40:28.389312 +0:00	0 0:1:10.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:38:22.640335 +0:00	0 0:1:4.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:36:40.354719 +0:00	0 0:1:22.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:34:31.97967 +0:00	0 0:1:14.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:32:47.074596 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:30:28.358342 +0:00	0 0:1:10.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:04:15.32883 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:02:15.135804 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 12:00:15.086532 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:58:15.12181 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:56:15.132717 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:54:15.070144 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:52:15.086689 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:50:15.078992 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:48:15.114781 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:46:15.224345 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:44:15.099373 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:42:15.142765 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:40:15.023871 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:38:15.064295 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:36:15.051495 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:34:15.088215 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:32:15.148771 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:30:15.070595 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:28:15.052641 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:26:15.197208 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:24:15.166959 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:22:15.043699 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:20:15.035814 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:18:15.143941 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:16:15.115612 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:14:15.092049 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:12:15.105867 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:10:15.097618 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:08:15.312819 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:07:21.070678 +0:00	0 0:1:6.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:04:14.08028 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:02:14.194759 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 11:00:14.055032 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:58:14.37419 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:56:14.107564 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:54:14.144042 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:52:14.208416 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:50:14.024753 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:48:14.081256 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:46:14.11444 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:44:14.124062 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:42:14.139809 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:40:14.142039 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:38:14.087897 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:36:14.142848 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:34:14.165422 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:32:14.166103 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:30:14.076308 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:28:14.153676 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:26:14.14524 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:24:14.182408 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:22:14.672571 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:20:14.591057 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:19:14.044585 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:18:16.109779 +0:00	0 0:1:2.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:15:14.04698 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:13:14.039003 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:11:14.876637 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-14 10:09:14.83428 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:28:23.038793 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:26:23.032779 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:24:23.053199 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:22:23.057851 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:20:23.073585 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:18:23.022244 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:16:23.019587 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:14:23.408513 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:12:23.194726 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:10:23.069954 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:08:23.108862 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:06:23.141496 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:04:23.128427 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:02:23.032492 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 17:00:23.089746 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:58:23.13132 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:56:23.142703 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:54:23.113189 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:52:23.224416 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:50:23.156474 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:48:23.040083 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:46:23.095798 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:44:23.2373 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:42:23.157322 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:40:23.122621 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:38:23.159377 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:36:23.191843 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:34:23.174665 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:32:23.683418 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 16:29:27.479741 +0:00	0 0:0:0.0	ORA-06575: Package or function LOAD_EXTRACT_TABLE is in an invalid state 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:20:01.161172 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:18:01.046239 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:16:01.081841 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:14:01.088241 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:12:01.030951 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:10:01.049036 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:08:01.135521 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:06:01.050842 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:04:01.157444 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:02:01.132989 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 11:00:01.19305 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:58:01.196252 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:56:01.123907 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:54:01.182451 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:52:01.177749 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:50:01.170707 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:48:01.103162 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:46:01.064399 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:44:01.173375 +0:00	0 0:0:0.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:42:16.314975 +0:00	0 0:0:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:41:50.736113 +0:00	0 0:1:50.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:39:28.157574 +0:00	0 0:1:27.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:37:16.053526 +0:00	0 0:1:15.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:35:31.524602 +0:00	0 0:1:30.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:33:41.20966 +0:00	0 0:1:40.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:31:29.388486 +0:00	0 0:1:28.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:29:33.441387 +0:00	0 0:1:32.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:27:28.167733 +0:00	0 0:1:27.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:25:47.911226 +0:00	0 0:1:46.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:23:27.022483 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	SUCCEEDED	2025-09-13 10:06:15.998808 +0:00	0 0:1:25.0	null
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 10:02:51.61306 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 10:00:51.632321 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:58:51.655402 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:56:51.661941 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:54:51.575825 +0:00	0 0:0:0.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:52:51.608849 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:50:51.628076 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:48:51.22546 +0:00	0 0:0:0.0	ORA-20046: Profile GENAI_GRAPH does not exist. ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:46:51.077123 +0:00	0 0:0:0.0	ORA-20046: Profile GENAI_GRAPH does not exist. ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:44:51.650984 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:42:51.721013 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:40:51.572355 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:38:51.56547 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:36:51.673014 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:34:51.620102 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:32:51.594526 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:30:51.570188 +0:00	0 0:0:0.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:28:51.680196 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:26:51.539529 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:24:51.532816 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:22:51.761599 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:20:51.60513 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:18:51.549427 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:16:51.581779 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:14:56.62371 +0:00	0 0:0:6.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:12:51.71743 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:10:51.590893 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:08:52.147643 +0:00	0 0:0:1.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> RUNEXTRACTSTAGINGSTOREDPROCEDURE	FAILED	2025-09-13 09:06:56.759611 +0:00	0 0:0:5.0	ORA-20401: Authorization failed for URI - https://inference.generativeai.us-chicago-1.oci.my$cloud_domain/20231130/actions/chat ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD", line 2243 ORA-06512: at "C##CLOUD$SERVICE.DBMS_CLOUD_AI", line 17412 ORA-06512: at "GRAPHUSER.EXTRACT_GRAPH", line 3 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 ORA-06512: at "GRAPHUSER.LOAD_EXTRACT_TABLE", line 18 
> DBMS_JOB$_3	SUCCEEDED	2025-09-12 09:02:35.20877 +0:00	0 0:0:0.0	null
> DBMS_JOB$_2	SUCCEEDED	2025-09-12 09:01:32.686757 +0:00	0 0:0:0.0	null
> DBMS_JOB$_1	SUCCEEDED	2025-09-12 09:01:27.6384 +0:00	0 0:0:0.0	null

This query counts how many text chunks in the main chunks table (**STORY_TABLE_CHUNKS**) have NOT yet been processed and added to the staging table (**GRAPH_EXTRACTION_STAGING**).

Query count **must come down to 0** before continuing.

This query counts how many text chunks in the main chunks table (STORY_TABLE_CHUNKS) have NOT yet been processed and added to the staging table (GRAPH_EXTRACTION_STAGING).

Query count must come down to 0 before continuing.

```sql
SELECT count(*)  AS "Chunks of Text to Send"
FROM  STORY_TABLE_CHUNKS c 
LEFT JOIN  GRAPH_EXTRACTION_STAGING S ON S.CHUNK_ID  = c.chunk_id
WHERE s.chunk_id IS NULL;
```

> Chunks of Text to Send
> 0

**TEST EMBEDDINGS**

TEST EMBEDDINGS

```sql
WITH q AS (
  SELECT DBMS_VECTOR.UTL_TO_EMBEDDING(
           'Kje Piki Jakob in njegov prijatelj najraje preživljata čas skupaj?',
           JSON(q'~{
             "provider":"ocigenai",
             "credential_name":"OCI_GENAI_CRED_GRAPH",
             "url":"https://inference.generativeai.eu-frankfurt-1.oci.oraclecloud.com/20231130/actions/embedText",
             "model":"cohere.embed-multilingual-v3.0"
           }~')
         ) AS qv
  FROM dual
)
SELECT t.doc_id, t.chunk_id, t.chunk_data,vector_distance(t.chunk_embedding, q.qv, COSINE) distance
FROM   STORY_TABLE_CHUNKS t
CROSS  JOIN q
WHERE  t.chunk_embedding IS NOT NULL
  AND  vector_dims(t.chunk_embedding) = vector_dims(q.qv)
ORDER  BY vector_distance(t.chunk_embedding, q.qv, COSINE)
FETCH FIRST 20 ROWS ONLY;
```

> DOC_ID	CHUNK_ID	CHUNK_DATA	DISTANCE
> 1	1	Moj prijatelj Piki Jakob Kdo je Piki Piki ne stanuje v gozdu, ne v živalskem vrtu, ne v cirkusu, ne v trgovini. Piki stanuje v bloku, v četrtem nadstropju, na polici za igrače. Pikiju je ime Piki, čeprav ni pikast. Tako mu je pač ime. Ni namreč vsakdo belec, ki se Belec piše, in tudi vode ne pije vsakdo, ki se piše Vodopivec. Tako je tudi Pikiju ime Piki. Piki hodi v medvedjo šolo in ima učitelja, ki ni medved, ampak fantek.	0.36838831789804993
> 1	66	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.	0.3828556104693558
> 1	64	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.	0.38344690348084065
> 1	2	Jaz sem učiteljev oče in zato dobro poznam Pikija in učitelja. Včasih se skupaj igramo človek ne jezi se. S Pikijem se dobro razumeva, z učiteljem pa imam včasih težave. Piki zmeraj pametno molči, učitelj pa mi včasih ugovarja. Nič ne pomaga, če mu rečem, da sem jaz ravnatelj. Pikiju ni nikoli dolgčas. Vsako jutro se z medvedjo kočijo, v kateri je nekoč učiteljeva starjša sestra prevažala punčke, odpelje v medvedjo šolo.	0.3975971400578723
> 1	42	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.	0.3998816730426653
> 1	37	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«	0.4035182254277364
> 1	147	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.	0.409794839903844
> 1	4	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.	0.4108946268900162
> 1	38	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.	0.41097468534569537
> 1	35	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.	0.4154715123245095
> 1	50	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.	0.42128432506756586
> 1	61	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.	0.4235298579574539
> 1	54	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«	0.4259643689858934
> 1	146	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«	0.42670250057928294
> 1	142	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«	0.4274407493825406
> 1	62	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.	0.42767793095392426
> 1	85	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.	0.4322354876178348
> 1	33	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.	0.4326232162908402
> 1	87	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.	0.4327757385383718
> 1	89	Žal je v temi slabo preračunala smer in padla naravnost v stari lavor, ki ga je učitelj spremenil v ribnik. Nastala je strašna povodenj, smrt pa je iz lavorja v podobi mokrega mačka jadrno švignila na balkon. Piki in Josip Jupiter sta se imenitno zabavala. Vsakemu, ki ju je hotel poslušati, sta pripovedovala, da sta držala smrt že za rep in je le malo manjkalo, pa bi jo stlačila v vrečo. Zatrjevala sta, da tako sijajnega novoletnega sejma še ni bilo. Manj navdušenja pa je kazal učitelj.	0.4335685063678838

At this stage, we could continue by sending these data chunks to the LLM to generate meaningful answers.
However, instead of relying on vector search and embeddings, we’ll add an additional step — using a **SQL Property Graph** to extract and analyze data chunks based on the relationships between entities identified within the text.

At this stage, we could continue by sending these data chunks to the LLM to generate meaningful answers.
However, instead of relying on vector search and embeddings, we’ll add an additional step — using a SQL Property Graph to extract and analyze data chunks based on the relationships between entities identified within the text.

In order to proceed we will need to create a few additional database tables and objects such as SQL property graph.

Procedure **LOAD_EXTRACT_TABLE** at the end generated **GRAPH_EXTRACTION_STAGING** table, which has the following content:

In order to proceed we will need to create a few additional database tables and objects such as SQL property graph.

Procedure LOAD_EXTRACT_TABLE at the end generated GRAPH_EXTRACTION_STAGING table, which has the following content:

```sql
select * from GRAPH_EXTRACTION_STAGING
FETCH FIRST 5 ROWS ONLY;
```

> CHUNK_ID	RESPONSE
> 11	[   {"head":"mama","head_type":"oseba","relation":"ne ve","tail":"učiteljevo mnenje","tail_type":"značilnost","data_chunk":"Mama tega še ni slišala"},   {"head":"učitelj","head_type":"oseba","relation":"ostane pri","tail":"svojem mnenju","tail_type":"značilnost","data_chunk":"tako je ostal učitelj pri svojem"},   {"head":"Piki","head_type":"oseba","relation":"sedel","tail":"polica","tail_type":"prostor","data_chunk":"Piki pa je zadovoljno sedel na polici"},   {"head":"Piki","head_type":"oseba","relation":"je zdrav","tail":"zdravje","tail_type":"značilnost","data_chunk":"vse je kazalo, da zaradi francoske solate ne bo umrl"},   {"head":"medvedji šola","head_type":"prostor","relation":"vsebuje","tail":"ura","tail_type":"dogodek","data_chunk":"V medvedji šoli so se učili o živalih"},   {"head":"učitelj","head_type":"oseba","relation":"uči","tail":"medvedi","tail_type":"oseba","data_chunk":"Učitelj je kazal slike in oponašal živalske glasove"},   {"head":"učitelj","head_type":"oseba","relation":"ponavlja","tail":"medvedi","tail_type":"oseba","data_chunk":"Potem so ponavljali"},   {"head":"učitelj","head_type":"oseba","relation":"vpraša","tail":"medvedi","tail_type":"oseba","data_chunk":"»Kdo je to?« je vprašal učitelj"} ]
> 12	[   {"head": "Filip", "head_type": "oseba", "relation": "odgovarja", "tail": "učitelj", "tail_type": "oseba", "data_chunk": "je odgovoril Filip"},   {"head": "učitelj", "head_type": "oseba", "relation": "pogovarja se", "tail": "Filip", "tail_type": "oseba", "data_chunk": "je rekel učitelj"},   {"head": "Timika", "head_type": "oseba", "relation": "odgovarja", "tail": "učitelj", "tail_type": "oseba", "data_chunk": "je odgovorila Timika"},   {"head": "učitelj", "head_type": "oseba", "relation": "pogovarja se", "tail": "Timika", "tail_type": "oseba", "data_chunk": "je rekel učitelj"},   {"head": "Piki Jakob", "head_type": "oseba", "relation": "odgovarja", "tail": "učitelj", "tail_type": "oseba", "data_chunk": "je rekel Piki"},   {"head": "učitelj", "head_type": "oseba", "relation": "pogovarja se", "tail": "Piki Jakob", "tail_type": "oseba", "data_chunk": "je rekel učitelj"},   {"head": "Piki Jakob", "head_type": "oseba", "relation": "govori o", "tail": "mačke", "tail_type": "žival", "data_chunk": "kaj veš o mačkah"},   {"head": "mačke", "head_type": "žival", "relation": "izdajajo zvok", "tail": "mijavkanje", "tail_type": "značilnost", "data_chunk": "mačke mijavkajo"},   {"head": "mačke", "head_type": "žival", "relation": "izdajajo zvok", "tail": "žvižganje", "tail_type": "značilnost", "data_chunk": "mačke žvižgajo"},   {"head": "ptički", "head_type": "žival", "relation": "izdajajo zvok", "tail": "gostolij", "tail_type": "značilnost", "data_chunk": "ptički gostolijo"},   {"head": "ptički", "head_type": "žival", "relation": "izdajajo zvok", "tail": "žvrgolij", "tail_type": "značilnost", "data_chunk": "ptički žvrgolijo"},   {"head": "ptički", "head_type": "žival", "relation": "izdajajo zvok", "tail": "žvižganje", "tail_type": "značilnost", "data_chunk": "ptički žvižgajo"},   {"head": "pes", "head_type": "žival", "relation": "izdajajo zvok", "tail": "lajanje", "tail_type": "značilnost", "data_chunk": "pes laja"} ]
> 1	[   {"head":"Piki Jakob","head_type":"oseba","relation":"stanuje","tail":"blok","tail_type":"prostor","data_chunk":"Piki stanuje v bloku"},   {"head":"Piki Jakob","head_type":"oseba","relation":"hodi v","tail":"medvedja šola","tail_type":"prostor","data_chunk":"Piki hodi v medvedjo šolo"},   {"head":"Piki Jakob","head_type":"oseba","relation":"ima učitelja","tail":"fantek","tail_type":"oseba","data_chunk":"ima učitelja, ki ni medved, ampak fantek"} ]
> 2	[   {"head":"Piki","head_type":"oseba","relation":"ima očeta","tail":"učiteljev oče","tail_type":"oseba","data_chunk":"Jaz sem učiteljev oče in zato dobro poznam Pikija"},   {"head":"Piki","head_type":"oseba","relation":"se razumeva","tail":"učiteljev oče","tail_type":"oseba","data_chunk":"S Pikijem se dobro razumeva"},   {"head":"učitelj","head_type":"oseba","relation":"ima očeta","tail":"učiteljev oče","tail_type":"oseba","data_chunk":"Jaz sem učiteljev oče"},   {"head":"učitelj","head_type":"oseba","relation":"ima težave","tail":"učiteljev oče","tail_type":"oseba","data_chunk":"z učiteljem pa imam včasih težave"},   {"head":"Piki","head_type":"oseba","relation":"hodi v","tail":"medvedja šola","tail_type":"prostor","data_chunk":"Vsako jutro se z medvedjo kočijo, odpelje v medvedjo šolo"},   {"head":"Piki","head_type":"oseba","relation":"vozi","tail":"medvedja kočija","tail_type":"predmet","data_chunk":"Vsako jutro se z medvedjo kočijo, odpelje v medvedjo šolo"} ]
> 3	[   {"head":"Marko","head_type":"oseba","relation":"je","tail":"medved","tail_type":"oseba","data_chunk":"Dvema ali trem je ime Marko"},   {"head":"Filip","head_type":"oseba","relation":"je","tail":"medved","tail_type":"oseba","data_chunk":"Eden je Filip"},   {"head":"Timika","head_type":"oseba","relation":"je","tail":"medved","tail_type":"oseba","data_chunk":"majhni medvedki je ime Timika"},   {"head":"Josip Jupiter","head_type":"oseba","relation":"je","tail":"medved","tail_type":"oseba","data_chunk":"Potem so tukaj še Josip Jupiter"},   {"head":"Benjamin","head_type":"oseba","relation":"je","tail":"medved","tail_type":"oseba","data_chunk":"Potem so tukaj še Josip Jupiter, Benjamin"},   {"head":"Floki","head_type":"oseba","relation":"je","tail":"pes","tail_type":"žival","data_chunk":"Floki, ki sicer ni medved, ampak pes"},   {"head":"Floki","head_type":"oseba","relation":"hodi v","tail":"medvedja šola","tail_type":"prostor","data_chunk":"hodi v medvedjo šolo"},   {"head":"Piki","head_type":"oseba","relation":"je","tail":"leteči medved","tail_type":"značilnost","data_chunk":"Piki včasih tudi leteči medved"},   {"head":"učitelj","head_type":"oseba","relation":"spiva z","tail":"Floki","tail_type":"oseba","data_chunk":"Z učiteljem spiva v isti sobi"} ]

We are now going to use **GRAPH_EXTRACTION_STAGING** table to prepare data table which we will use for the property graph build.

We are now going to use GRAPH_EXTRACTION_STAGING table to prepare data table which we will use for the property graph build.

```sql
BEGIN
---------------------------------------------------------------------------
  -- Drop and recreate GRAPH_RELATIONS_STG
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE GRAPH_RELATIONS_STG PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF;
  END;

  EXECUTE IMMEDIATE 'CREATE TABLE GRAPH_RELATIONS_STG (
        id              RAW(16) DEFAULT SYS_GUID() PRIMARY KEY,
        chunk_id        NUMBER,
        head            VARCHAR(256) NOT NULL,
        head_type       VARCHAR(256),
        relation        VARCHAR(256) NOT NULL,
        tail            VARCHAR(256) NOT NULL,
        tail_type       VARCHAR(256),
        text            VARCHAR(512),
        chunk_data      VARCHAR(4000)
  )';
END;
```

> PL/SQL procedure successfully completed.

Read and populate **GRAPH_RELATIONS_STG** from **GRAPH_EXTRACTION_STAGING**

Read and populate GRAPH_RELATIONS_STG from GRAPH_EXTRACTION_STAGING

```sql
INSERT INTO GRAPH_RELATIONS_STG (chunk_id, head, head_type, relation, tail, tail_type, text, chunk_data)
    SELECT mt.chunk_id, jt.head, jt.head_type, jt.relation, jt.tail, jt.tail_type, jt.head_type || ': ' || jt.head ||
    ' -[' || jt.relation || ']-> ' || jt.tail_type || ': ' || jt.tail, ch.chunk_data
    FROM GRAPH_EXTRACTION_STAGING mt,
    STORY_TABLE_CHUNKS ch,
    JSON_TABLE (
        mt.RESPONSE,
        '$[*]'
        COLUMNS (
            head VARCHAR2(256) PATH '$.head',
            head_type VARCHAR2(256) PATH '$.head_type',
            relation VARCHAR2(256) PATH '$.relation',
            tail VARCHAR2(256) PATH '$.tail',
            tail_type VARCHAR2(256) PATH '$.tail_type'
        )
    ) jt WHERE
    ch.chunk_id = mt.chunk_id and
    mt.response is json and
    jt.head IS NOT NULL and
    jt.relation IS NOT NULL and
    jt.tail IS NOT NULL;
```

> Query executed successfully. Affected rows : 1017

```sql
select * from GRAPH_RELATIONS_STG;
```

> ID	CHUNK_ID	HEAD	HEAD_TYPE	RELATION	TAIL	TAIL_TYPE	TEXT	CHUNK_DATA
> 40FAFD14510B6243E063AB11000AF774	31	medvedja mamica	oseba	ima lastnost	rada	značilnost	oseba: medvedja mamica -[ima lastnost]-> značilnost: rada	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD14510C6243E063AB11000AF774	31	medvedja mamica	oseba	se pogovarja	medvedki	predmet	oseba: medvedja mamica -[se pogovarja]-> predmet: medvedki	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD14510D6243E063AB11000AF774	31	Piki	oseba	govori	učitelj	oseba	oseba: Piki -[govori]-> oseba: učitelj	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD14510E6243E063AB11000AF774	31	učitelj	oseba	vpraša	Piki	oseba	oseba: učitelj -[vpraša]-> oseba: Piki	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD14510F6243E063AB11000AF774	31	Piki	oseba	govori	učitelj	oseba	oseba: Piki -[govori]-> oseba: učitelj	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD1451106243E063AB11000AF774	31	učitelj	oseba	odgovarja	Piki	oseba	oseba: učitelj -[odgovarja]-> oseba: Piki	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD1451116243E063AB11000AF774	31	Piki	oseba	trdi	medvedja mamica	oseba	oseba: Piki -[trdi]-> oseba: medvedja mamica	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 40FAFD1451126243E063AB11000AF774	32	medvedja mamica	oseba	dela	možakar	oseba	oseba: medvedja mamica -[dela]-> oseba: možakar	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451136243E063AB11000AF774	32	možakar	oseba	prezema	medvedki	predmet	oseba: možakar -[prezema]-> predmet: medvedki	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451146243E063AB11000AF774	32	medvedki	predmet	prevozi	trgovina	prostor	predmet: medvedki -[prevozi]-> prostor: trgovina	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451156243E063AB11000AF774	32	trgovina	prostor	dela	medvedki	predmet	prostor: trgovina -[dela]-> predmet: medvedki	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451166243E063AB11000AF774	32	medvedki	predmet	ima lastnost	listek	značilnost	predmet: medvedki -[ima lastnost]-> značilnost: listek	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451176243E063AB11000AF774	32	Piki	oseba	se nahaja	izložba	prostor	oseba: Piki -[se nahaja]-> prostor: izložba	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451186243E063AB11000AF774	32	Piki	oseba	vzpostavi stik	očeta	oseba	oseba: Piki -[vzpostavi stik]-> oseba: očeta	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD1451196243E063AB11000AF774	32	očeta	oseba	kupi	Piki	oseba	oseba: očeta -[kupi]-> oseba: Piki	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 40FAFD14511A6243E063AB11000AF774	33	učitelj	oseba	poboža	Piki	oseba	oseba: učitelj -[poboža]-> oseba: Piki	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD14511B6243E063AB11000AF774	33	učitelj	oseba	sanja	medvedja mamica	oseba	oseba: učitelj -[sanja]-> oseba: medvedja mamica	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD14511C6243E063AB11000AF774	33	medvedja mamica	oseba	proizvaja	medvedki	predmet	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD14511D6243E063AB11000AF774	33	učitelj	oseba	piše	pismo	dokument	oseba: učitelj -[piše]-> dokument: pismo	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD14511E6243E063AB11000AF774	33	učitelj	oseba	pošilja	babi	oseba	oseba: učitelj -[pošilja]-> oseba: babi	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD14511F6243E063AB11000AF774	33	učitelj	oseba	pošilja	ded	oseba	oseba: učitelj -[pošilja]-> oseba: ded	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD1451206243E063AB11000AF774	33	učitelj	oseba	pošilja	Piki	oseba	oseba: učitelj -[pošilja]-> oseba: Piki	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD1451216243E063AB11000AF774	33	Piki	oseba	vpraša	učitelj	oseba	oseba: Piki -[vpraša]-> oseba: učitelj	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 40FAFD1451226243E063AB11000AF774	34	Piki	oseba	stanuje	Ljubljana	prostor	oseba: Piki -[stanuje]-> prostor: Ljubljana	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 40FAFD1451236243E063AB11000AF774	34	Piki	oseba	piše	Žužu številka 2	oseba	oseba: Piki -[piše]-> oseba: Žužu številka 2	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 40FAFD1451246243E063AB11000AF774	34	Piki	oseba	živi z	učitelj	oseba	oseba: Piki -[živi z]-> oseba: učitelj	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 40FAFD1451256243E063AB11000AF774	34	Piki	oseba	se spominja	Žužu številka 2	oseba	oseba: Piki -[se spominja]-> oseba: Žužu številka 2	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 40FAFD1451266243E063AB11000AF774	34	Piki	oseba	ima vzdevek	Žužu številka 1	značilnost	oseba: Piki -[ima vzdevek]-> značilnost: Žužu številka 1	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 40FAFD1451276243E063AB11000AF774	35	Piki Jakob	oseba	živi	Ljubljana	prostor	oseba: Piki Jakob -[živi]-> prostor: Ljubljana	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD1451286243E063AB11000AF774	35	Piki Jakob	oseba	hodi v šolo	medvedja šola	prostor	oseba: Piki Jakob -[hodi v šolo]-> prostor: medvedja šola	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD1451296243E063AB11000AF774	35	Piki Jakob	oseba	ima prijatelje	medvedji prijatelji	oseba	oseba: Piki Jakob -[ima prijatelje]-> oseba: medvedji prijatelji	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD14512A6243E063AB11000AF774	35	Piki Jakob	oseba	piše	neznani prejemnik	oseba	oseba: Piki Jakob -[piše]-> oseba: neznani prejemnik	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD14512B6243E063AB11000AF774	35	Piki Jakob	oseba	pošlje pismo	pošta	prostor	oseba: Piki Jakob -[pošlje pismo]-> prostor: pošta	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD14512C6243E063AB11000AF774	35	Piki Jakob	oseba	ima učitelja	učitelj	oseba	oseba: Piki Jakob -[ima učitelja]-> oseba: učitelj	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 40FAFD14512D6243E063AB11000AF774	36	Piki	oseba	piše	Tedi	oseba	oseba: Piki -[piše]-> oseba: Tedi	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD14512E6243E063AB11000AF774	36	Piki	oseba	piše	Marmeladov	oseba	oseba: Piki -[piše]-> oseba: Marmeladov	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD14512F6243E063AB11000AF774	36	Piki	oseba	piše	Berenson	oseba	oseba: Piki -[piše]-> oseba: Berenson	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451306243E063AB11000AF774	36	Piki	oseba	piše	Medolizis	oseba	oseba: Piki -[piše]-> oseba: Medolizis	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451316243E063AB11000AF774	36	Piki	oseba	piše	Mečkovič	oseba	oseba: Piki -[piše]-> oseba: Mečkovič	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451326243E063AB11000AF774	36	Piki	oseba	prejme pismo	Žužu	oseba	oseba: Piki -[prejme pismo]-> oseba: Žužu	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451336243E063AB11000AF774	36	Žužu	oseba	vozi	metro	predmet	oseba: Žužu -[vozi]-> predmet: metro	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451346243E063AB11000AF774	36	medvedi v Parizu	oseba	jedajo	med	značilnost	oseba: medvedi v Parizu -[jedajo]-> značilnost: med	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451356243E063AB11000AF774	36	medvedi v Parizu	oseba	hodijo	šola	prostor	oseba: medvedi v Parizu -[hodijo]-> prostor: šola	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451366243E063AB11000AF774	36	medvedi v Parizu	oseba	vozijo	metro	predmet	oseba: medvedi v Parizu -[vozijo]-> predmet: metro	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 40FAFD1451376243E063AB11000AF774	37	učitelj	oseba	poisal	Ljubljana	prostor	oseba: učitelj -[poisal]-> prostor: Ljubljana	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD1451386243E063AB11000AF774	37	Ljubljana	prostor	je blizu	morje	prostor	prostor: Ljubljana -[je blizu]-> prostor: morje	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD1451396243E063AB11000AF774	37	Žužu	oseba	pošlje pismo	Piki Jakob	oseba	oseba: Žužu -[pošlje pismo]-> oseba: Piki Jakob	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD14513A6243E063AB11000AF774	37	poštar	oseba	išče	Piki Jakob	oseba	oseba: poštar -[išče]-> oseba: Piki Jakob	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD14513B6243E063AB11000AF774	37	Piki Jakob	oseba	stanuje	blok	prostor	oseba: Piki Jakob -[stanuje]-> prostor: blok	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD14513C6243E063AB11000AF774	37	poštar	oseba	pozvonil	stopnišče	prostor	oseba: poštar -[pozvonil]-> prostor: stopnišče	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 40FAFD14513D6243E063AB11000AF774	38	Piki Jakob	oseba	prejme pismo	poštar	oseba	oseba: Piki Jakob -[prejme pismo]-> oseba: poštar	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 40FAFD14513E6243E063AB11000AF774	38	Piki Jakob	oseba	stanuje	učitelj	oseba	oseba: Piki Jakob -[stanuje]-> oseba: učitelj	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 40FAFD14513F6243E063AB11000AF774	38	Piki Jakob	oseba	ima poštno skrinjico	poštna skrinjica	predmet	oseba: Piki Jakob -[ima poštno skrinjico]-> predmet: poštna skrinjica	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 40FAFD1451406243E063AB11000AF774	38	poštar	oseba	išče	Piki Jakob	oseba	oseba: poštar -[išče]-> oseba: Piki Jakob	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 40FAFD1451416243E063AB11000AF774	38	učitelj	oseba	ima podnajemnika	Piki Jakob	oseba	oseba: učitelj -[ima podnajemnika]-> oseba: Piki Jakob	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 40FAFD1451426243E063AB11000AF774	39	Piki	oseba	je član	družina	skupina	oseba: Piki -[je član]-> skupina: družina	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451436243E063AB11000AF774	39	Piki	oseba	ima zobobol	zobobol	značilnost	oseba: Piki -[ima zobobol]-> značilnost: zobobol	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451446243E063AB11000AF774	39	Piki	oseba	obiskuje	zobozdravnik	oseba	oseba: Piki -[obiskuje]-> oseba: zobozdravnik	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451456243E063AB11000AF774	39	učitelj	oseba	ima zobobol	zobobol	značilnost	oseba: učitelj -[ima zobobol]-> značilnost: zobobol	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451466243E063AB11000AF774	39	govorec	oseba	ima zobobol	zobobol	značilnost	oseba: govorec -[ima zobobol]-> značilnost: zobobol	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451476243E063AB11000AF774	39	Piki	oseba	prejema zdravstvo	obkladke	predmet	oseba: Piki -[prejema zdravstvo]-> predmet: obkladke	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 40FAFD1451486243E063AB11000AF774	40	Piki	oseba	ima težavo	uši	značilnost	oseba: Piki -[ima težavo]-> značilnost: uši	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD1451496243E063AB11000AF774	40	Piki	oseba	obvezan z	ruto	predmet	oseba: Piki -[obvezan z]-> predmet: ruto	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514A6243E063AB11000AF774	40	Piki	oseba	obiskuje	zobozdravnik	oseba	oseba: Piki -[obiskuje]-> oseba: zobozdravnik	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514B6243E063AB11000AF774	40	učitelj	oseba	svetuje	Piki	oseba	oseba: učitelj -[svetuje]-> oseba: Piki	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514C6243E063AB11000AF774	40	zobozdravnik	oseba	je prijatelj	Piki	oseba	oseba: zobozdravnik -[je prijatelj]-> oseba: Piki	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514D6243E063AB11000AF774	40	Piki	oseba	se strinja	učitelj	oseba	oseba: Piki -[se strinja]-> oseba: učitelj	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514E6243E063AB11000AF774	40	učitelj	oseba	svetuje	Piki	oseba	oseba: učitelj -[svetuje]-> oseba: Piki	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 40FAFD14514F6243E063AB11000AF774	41	Piki	oseba	se strinja	učitelj	oseba	oseba: Piki -[se strinja]-> oseba: učitelj	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451506243E063AB11000AF774	41	učitelj	oseba	svetuje	Piki	oseba	oseba: učitelj -[svetuje]-> oseba: Piki	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451516243E063AB11000AF774	41	Piki	oseba	potrpi	zobozdravnik	oseba	oseba: Piki -[potrpi]-> oseba: zobozdravnik	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451526243E063AB11000AF774	41	Piki	oseba	je obvezan	ruto	predmet	oseba: Piki -[je obvezan]-> predmet: ruto	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451536243E063AB11000AF774	41	učitelj	oseba	vpraša	otrok	oseba	oseba: učitelj -[vpraša]-> oseba: otrok	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451546243E063AB11000AF774	41	medved	oseba	more biti bolan	zob	značilnost	oseba: medved -[more biti bolan]-> značilnost: zob	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 40FAFD1451556243E063AB11000AF774	42	Piki	oseba	sedel	stol	predmet	oseba: Piki -[sedel]-> predmet: stol	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD1451566243E063AB11000AF774	42	Piki	oseba	ima zdravstveno knjižico	zdravstvena knjižica	dokument	oseba: Piki -[ima zdravstveno knjižico]-> dokument: zdravstvena knjižica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD1451576243E063AB11000AF774	42	bolniška sestra	oseba	pobira	zdravstvena knjižica	dokument	oseba: bolniška sestra -[pobira]-> dokument: zdravstvena knjižica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD1451586243E063AB11000AF774	42	Piki	oseba	se sreča	bolniška sestra	oseba	oseba: Piki -[se sreča]-> oseba: bolniška sestra	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD1451596243E063AB11000AF774	42	Piki	oseba	čaka	čakalnica	prostor	oseba: Piki -[čaka]-> prostor: čakalnica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD14515A6243E063AB11000AF774	42	bolniška sestra	oseba	kliče	Piki Jakob	oseba	oseba: bolniška sestra -[kliče]-> oseba: Piki Jakob	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD14515B6243E063AB11000AF774	42	Piki Jakob	oseba	obiskuje	zdravnik	oseba	oseba: Piki Jakob -[obiskuje]-> oseba: zdravnik	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD14515C6243E063AB11000AF774	42	zdravnik	oseba	pozdravlja	Piki Jakob	oseba	oseba: zdravnik -[pozdravlja]-> oseba: Piki Jakob	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD14515D6243E063AB11000AF774	42	Piki Jakob	oseba	ima težavo	zobobol	značilnost	oseba: Piki Jakob -[ima težavo]-> značilnost: zobobol	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 40FAFD14515E6243E063AB11000AF774	43	zdravnik	oseba	zdravi	Piki	oseba	oseba: zdravnik -[zdravi]-> oseba: Piki	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD14515F6243E063AB11000AF774	43	Piki	oseba	sedel	stol	predmet	oseba: Piki -[sedel]-> predmet: stol	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD1451606243E063AB11000AF774	43	zdravnik	oseba	preiskuje	Piki	oseba	oseba: zdravnik -[preiskuje]-> oseba: Piki	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD1451616243E063AB11000AF774	43	zdravnik	oseba	uporablja	kovinska paličica	predmet	oseba: zdravnik -[uporablja]-> predmet: kovinska paličica	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD1451626243E063AB11000AF774	43	Piki	oseba	odgovarja	zdravnik	oseba	oseba: Piki -[odgovarja]-> oseba: zdravnik	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD1451636243E063AB11000AF774	43	Piki	oseba	ima bolečino	zob	značilnost	oseba: Piki -[ima bolečino]-> značilnost: zob	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 40FAFD1451646243E063AB11000AF774	44	zdravnik	oseba	preiskuje	Piki	oseba	oseba: zdravnik -[preiskuje]-> oseba: Piki	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD1451656243E063AB11000AF774	44	zdravnik	oseba	uporablja	prst	predmet	oseba: zdravnik -[uporablja]-> predmet: prst	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD1451666243E063AB11000AF774	44	Piki	oseba	čuti bolečino	zob	značilnost	oseba: Piki -[čuti bolečino]-> značilnost: zob	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD1451676243E063AB11000AF774	44	Piki	oseba	grize	zdravnik	oseba	oseba: Piki -[grize]-> oseba: zdravnik	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD1451686243E063AB11000AF774	44	zdravnik	oseba	ukazuje	Piki	oseba	oseba: zdravnik -[ukazuje]-> oseba: Piki	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD1451696243E063AB11000AF774	44	Piki	oseba	se izogiba	zdravnik	oseba	oseba: Piki -[se izogiba]-> oseba: zdravnik	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 40FAFD14516A6243E063AB11000AF774	45	Piki	oseba	ima zob	zob	predmet	oseba: Piki -[ima zob]-> predmet: zob	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD14516B6243E063AB11000AF774	45	učitelj	oseba	ima zob	zob	predmet	oseba: učitelj -[ima zob]-> predmet: zob	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD14516C6243E063AB11000AF774	45	učitelj	oseba	obiskuje	zobozdravnik	oseba	oseba: učitelj -[obiskuje]-> oseba: zobozdravnik	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD14516D6243E063AB11000AF774	45	zobozdravnik	oseba	plombira	učitelj	oseba	oseba: zobozdravnik -[plombira]-> oseba: učitelj	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD14516E6243E063AB11000AF774	45	zobozdravnik	oseba	pregleda	Piki	oseba	oseba: zobozdravnik -[pregleda]-> oseba: Piki	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD14516F6243E063AB11000AF774	45	Piki	oseba	odhaja	zobozdravnik	prostor	oseba: Piki -[odhaja]-> prostor: zobozdravnik	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 40FAFD1451706243E063AB11000AF774	46	Piki	oseba	ugrizne	zobozdravnik	oseba	oseba: Piki -[ugrizne]-> oseba: zobozdravnik	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451716243E063AB11000AF774	46	učitelj	oseba	govori	Piki	oseba	oseba: učitelj -[govori]-> oseba: Piki	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451726243E063AB11000AF774	46	Piki	oseba	odgovarja	učitelj	oseba	oseba: Piki -[odgovarja]-> oseba: učitelj	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451736243E063AB11000AF774	46	učitelj	oseba	opozarja	pripovedovalec	oseba	oseba: učitelj -[opozarja]-> oseba: pripovedovalec	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451746243E063AB11000AF774	46	medvedja šola	prostor	organizira	športni dan	dogodek	prostor: medvedja šola -[organizira]-> dogodek: športni dan	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451756243E063AB11000AF774	46	učitelj	oseba	pripravlja	vožnja z žičnico	aktivnost	oseba: učitelj -[pripravlja]-> aktivnost: vožnja z žičnico	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 40FAFD1451766243E063AB11000AF774	47	matador	oseba	sestavi	kabino	predmet	oseba: matador -[sestavi]-> predmet: kabino	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 40FAFD1451776243E063AB11000AF774	47	kabina	predmet	drsela	vrvi	predmet	predmet: kabina -[drsela]-> predmet: vrvi	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 40FAFD1451786243E063AB11000AF774	47	učitelj	oseba	naznani	spomladanski kros	dogodek	oseba: učitelj -[naznani]-> dogodek: spomladanski kros	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 40FAFD1451796243E063AB11000AF774	47	Timika	oseba	šeži	uho	predmet	oseba: Timika -[šeži]-> predmet: uho	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 40FAFD14517A6243E063AB11000AF774	47	Josip Jupiter	oseba	razpara	hlačnico	predmet	oseba: Josip Jupiter -[razpara]-> predmet: hlačnico	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 40FAFD14517B6243E063AB11000AF774	48	Piki	oseba	govori	Timika	oseba	oseba: Piki -[govori]-> oseba: Timika	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD14517C6243E063AB11000AF774	48	Timika	oseba	odgovarja	Piki	oseba	oseba: Timika -[odgovarja]-> oseba: Piki	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD14517D6243E063AB11000AF774	48	učitelj	oseba	pripravlja	proga	prostor	oseba: učitelj -[pripravlja]-> prostor: proga	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD14517E6243E063AB11000AF774	48	medvedji	oseba	tekajo	proga	prostor	oseba: medvedji -[tekajo]-> prostor: proga	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD14517F6243E063AB11000AF774	48	zmagovalec	oseba	prejme	zlato medaljo	predmet	oseba: zmagovalec -[prejme]-> predmet: zlato medaljo	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD1451806243E063AB11000AF774	48	zmagovalec	oseba	prejme	veliko hruško	predmet	oseba: zmagovalec -[prejme]-> predmet: veliko hruško	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 40FAFD1451816243E063AB11000AF774	49	medvedji	oseba	tekajo	berezov gaj	prostor	oseba: medvedji -[tekajo]-> prostor: berezov gaj	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451826243E063AB11000AF774	49	medvedji	oseba	tekajo	dnevna soba	prostor	oseba: medvedji -[tekajo]-> prostor: dnevna soba	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451836243E063AB11000AF774	49	medvedji	oseba	podrli	drevesa	predmet	oseba: medvedji -[podrli]-> predmet: drevesa	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451846243E063AB11000AF774	49	učitelj	oseba	postavi	drevesa	predmet	oseba: učitelj -[postavi]-> predmet: drevesa	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451856243E063AB11000AF774	49	fikus	predmet	izgubi	lista	predmet	predmet: fikus -[izgubi]-> predmet: lista	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451866243E063AB11000AF774	49	medvedji	oseba	tekajo	pusto planjavo	prostor	oseba: medvedji -[tekajo]-> prostor: pusto planjavo	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451876243E063AB11000AF774	49	medvedji	oseba	tekajo	hodnik	prostor	oseba: medvedji -[tekajo]-> prostor: hodnik	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451886243E063AB11000AF774	49	medvedji	oseba	imajo težave	močvirni predeli	prostor	oseba: medvedji -[imajo težave]-> prostor: močvirni predeli	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD1451896243E063AB11000AF774	49	medvedji	oseba	imajo težave	kopalnica	prostor	oseba: medvedji -[imajo težave]-> prostor: kopalnica	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD14518A6243E063AB11000AF774	49	Filip	oseba	pade	ribnik	prostor	oseba: Filip -[pade]-> prostor: ribnik	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD14518B6243E063AB11000AF774	49	Filip	oseba	pade	banjo	predmet	oseba: Filip -[pade]-> predmet: banjo	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 40FAFD14518C6243E063AB11000AF774	50	medvedji	oseba	tekajo	južno gričevje	prostor	oseba: medvedji -[tekajo]-> prostor: južno gričevje	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD14518D6243E063AB11000AF774	50	medvedji	oseba	tekajo	spalnica	prostor	oseba: medvedji -[tekajo]-> prostor: spalnica	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD14518E6243E063AB11000AF774	50	medvedji	oseba	srečajo	vzpon	značilnost	oseba: medvedji -[srečajo]-> značilnost: vzpon	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD14518F6243E063AB11000AF774	50	medvedji	oseba	srečajo	stari grad	prostor	oseba: medvedji -[srečajo]-> prostor: stari grad	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451906243E063AB11000AF774	50	medvedji	oseba	srečajo	omara	predmet	oseba: medvedji -[srečajo]-> predmet: omara	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451916243E063AB11000AF774	50	Piki	oseba	prileze	vrh	prostor	oseba: Piki -[prileze]-> prostor: vrh	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451926243E063AB11000AF774	50	Piki	oseba	teče	greben	prostor	oseba: Piki -[teče]-> prostor: greben	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451936243E063AB11000AF774	50	Piki	oseba	teče	temna goščava	prostor	oseba: Piki -[teče]-> prostor: temna goščava	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451946243E063AB11000AF774	50	Piki	oseba	teče	razmetane učiteljeve igrače	predmet	oseba: Piki -[teče]-> predmet: razmetane učiteljeve igrače	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451956243E063AB11000AF774	50	Piki	oseba	skoke	mehki travnik	prostor	oseba: Piki -[skoke]-> prostor: mehki travnik	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451966243E063AB11000AF774	50	Piki	oseba	skoke	postelja	predmet	oseba: Piki -[skoke]-> predmet: postelja	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 40FAFD1451976243E063AB11000AF774	51	Piki	oseba	drvi	mehki travnik	prostor	oseba: Piki -[drvi]-> prostor: mehki travnik	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD1451986243E063AB11000AF774	51	Piki	oseba	okleni	mehki travnik	prostor	oseba: Piki -[okleni]-> prostor: mehki travnik	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD1451996243E063AB11000AF774	51	Piki	oseba	spozna	hudi tiger	žival	oseba: Piki -[spozna]-> žival: hudi tiger	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD14519A6243E063AB11000AF774	51	Piki	oseba	spozna	maček	žival	oseba: Piki -[spozna]-> žival: maček	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD14519B6243E063AB11000AF774	51	medvedji športniki	oseba	vrže	hudi tiger	žival	oseba: medvedji športniki -[vrže]-> žival: hudi tiger	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD14519C6243E063AB11000AF774	51	hudi tiger	žival	zajaha	Piki	oseba	žival: hudi tiger -[zajaha]-> oseba: Piki	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 40FAFD14519D6243E063AB11000AF774	52	hudi tiger	žival	drvi	Piki	oseba	žival: hudi tiger -[drvi]-> oseba: Piki	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD14519E6243E063AB11000AF774	52	hudi tiger	žival	išče	odprto okno	predmet	žival: hudi tiger -[išče]-> predmet: odprto okno	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD14519F6243E063AB11000AF774	52	učitelj	oseba	zapre	okna	predmet	oseba: učitelj -[zapre]-> predmet: okna	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD1451A06243E063AB11000AF774	52	hudi tiger	žival	teče	kuhinja	prostor	žival: hudi tiger -[teče]-> prostor: kuhinja	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD1451A16243E063AB11000AF774	52	hudi tiger	žival	zavre	učitelj	oseba	žival: hudi tiger -[zavre]-> oseba: učitelj	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD1451A26243E063AB11000AF774	52	Piki	oseba	prileti	cilj	prostor	oseba: Piki -[prileti]-> prostor: cilj	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 40FAFD1451A36243E063AB11000AF774	53	Piki	oseba	prejme	zlato medaljo	predmet	oseba: Piki -[prejme]-> predmet: zlato medaljo	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A46243E063AB11000AF774	53	Piki	oseba	prejme	velikansko hruško	predmet	oseba: Piki -[prejme]-> predmet: velikansko hruško	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A56243E063AB11000AF774	53	tekmovalci	oseba	zaploskajo	Piki	oseba	oseba: tekmovalci -[zaploskajo]-> oseba: Piki	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A66243E063AB11000AF774	53	učitelj	oseba	potrdi	Pikijeva zmaga	dogodek	oseba: učitelj -[potrdi]-> dogodek: Pikijeva zmaga	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A76243E063AB11000AF774	53	Piki	oseba	jezdi	tiger	žival	oseba: Piki -[jezdi]-> žival: tiger	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A86243E063AB11000AF774	53	Piki	oseba	razdeli	hruško	predmet	oseba: Piki -[razdeli]-> predmet: hruško	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451A96243E063AB11000AF774	53	tiger	žival	bruši	kremplje	predmet	žival: tiger -[bruši]-> predmet: kremplje	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 40FAFD1451AA6243E063AB11000AF774	54	Piki	oseba	ima	vročino	zdravstvena stanja	oseba: Piki -[ima]-> zdravstvena stanja: vročino	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451AB6243E063AB11000AF774	54	medvedje	oseba	so	sami doma	značilnost	oseba: medvedje -[so]-> značilnost: sami doma	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451AC6243E063AB11000AF774	54	učitelj	oseba	odpelje	Sora	prostor	oseba: učitelj -[odpelje]-> prostor: Sora	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451AD6243E063AB11000AF774	54	Piki	oseba	sedel	zaboj za igrače	prostor	oseba: Piki -[sedel]-> prostor: zaboj za igrače	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451AE6243E063AB11000AF774	54	Piki	oseba	premišljeva	ohladitev	značilnost	oseba: Piki -[premišljeva]-> značilnost: ohladitev	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451AF6243E063AB11000AF774	54	Piki	oseba	zagleda	Stari Marko	oseba	oseba: Piki -[zagleda]-> oseba: Stari Marko	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451B06243E063AB11000AF774	54	Piki	oseba	pogovarja	Stari Marko	oseba	oseba: Piki -[pogovarja]-> oseba: Stari Marko	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 40FAFD1451B16243E063AB11000AF774	55	Stari Marko	oseba	zamomlja	Piki	oseba	oseba: Stari Marko -[zamomlja]-> oseba: Piki	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B26243E063AB11000AF774	55	Piki	oseba	zajavka	Stari Marko	oseba	oseba: Piki -[zajavka]-> oseba: Stari Marko	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B36243E063AB11000AF774	55	Stari Marko	oseba	predlaga	sončarica	zdravstvena stanja	oseba: Stari Marko -[predlaga]-> zdravstvena stanja: sončarica	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B46243E063AB11000AF774	55	Stari Marko	oseba	predlaga	kolera	zdravstvena stanja	oseba: Stari Marko -[predlaga]-> zdravstvena stanja: kolera	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B56243E063AB11000AF774	55	Piki	oseba	vzklika	Stari Marko	oseba	oseba: Piki -[vzklika]-> oseba: Stari Marko	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B66243E063AB11000AF774	55	Piki	oseba	razjezi	Stari Marko	oseba	oseba: Piki -[razjezi]-> oseba: Stari Marko	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B76243E063AB11000AF774	55	Stari Marko	oseba	svetuje	Piki	oseba	oseba: Stari Marko -[svetuje]-> oseba: Piki	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 40FAFD1451B86243E063AB11000AF774	56	Piki	oseba	ima lastnost	poten	značilnost	oseba: Piki -[ima lastnost]-> značilnost: poten	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451B96243E063AB11000AF774	56	Piki	oseba	uporablja	štadilnik	predmet	oseba: Piki -[uporablja]-> predmet: štadilnik	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BA6243E063AB11000AF774	56	Piki	oseba	uporablja	lonček za čaj	predmet	oseba: Piki -[uporablja]-> predmet: lonček za čaj	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BB6243E063AB11000AF774	56	Piki	oseba	uporablja	pokrovko	predmet	oseba: Piki -[uporablja]-> predmet: pokrovko	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BC6243E063AB11000AF774	56	Piki	oseba	uporablja	tableto	predmet	oseba: Piki -[uporablja]-> predmet: tableto	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BD6243E063AB11000AF774	56	Piki	oseba	dostopa	stenska lekarnica	prostor	oseba: Piki -[dostopa]-> prostor: stenska lekarnica	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BE6243E063AB11000AF774	56	stenska lekarnica	prostor	vsebuje	škatlice	predmet	prostor: stenska lekarnica -[vsebuje]-> predmet: škatlice	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 40FAFD1451BF6243E063AB11000AF774	57	Piki	oseba	pokliče	Stari Marko	oseba	oseba: Piki -[pokliče]-> oseba: Stari Marko	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C06243E063AB11000AF774	57	Piki	oseba	vpraša	Stari Marko	oseba	oseba: Piki -[vpraša]-> oseba: Stari Marko	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C16243E063AB11000AF774	57	Stari Marko	oseba	svetuje	aspirin	zdravilo	oseba: Stari Marko -[svetuje]-> zdravilo: aspirin	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C26243E063AB11000AF774	57	Piki	oseba	ima lastnost	neznanje	značilnost	oseba: Piki -[ima lastnost]-> značilnost: neznanje	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C36243E063AB11000AF774	57	Stari Marko	oseba	ima lastnost	znanje	značilnost	oseba: Stari Marko -[ima lastnost]-> značilnost: znanje	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C46243E063AB11000AF774	57	aspirin	zdravilo	zdravi	vročina	bolezen	zdravilo: aspirin -[zdravi]-> bolezen: vročina	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 40FAFD1451C56243E063AB11000AF774	58	Piki	oseba	zaužije	aspirin	zdravilo	oseba: Piki -[zaužije]-> zdravilo: aspirin	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451C66243E063AB11000AF774	58	Piki	oseba	pije	vroči lipov čaj	napitek	oseba: Piki -[pije]-> napitek: vroči lipov čaj	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451C76243E063AB11000AF774	58	Piki	oseba	ima lastnost	vročina	bolezen	oseba: Piki -[ima lastnost]-> bolezen: vročina	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451C86243E063AB11000AF774	58	Piki	oseba	ima lastnost	slabost	značilnost	oseba: Piki -[ima lastnost]-> značilnost: slabost	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451C96243E063AB11000AF774	58	Piki	oseba	se pogovarja	učitelj	oseba	oseba: Piki -[se pogovarja]-> oseba: učitelj	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451CA6243E063AB11000AF774	58	učitelj	oseba	vpraša	Piki	oseba	oseba: učitelj -[vpraša]-> oseba: Piki	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 40FAFD1451CB6243E063AB11000AF774	59	Piki	oseba	ima lastnost	vročina	bolezen	oseba: Piki -[ima lastnost]-> bolezen: vročina	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451CC6243E063AB11000AF774	59	učitelj	oseba	uporablja	toplomer	orodje	oseba: učitelj -[uporablja]-> orodje: toplomer	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451CD6243E063AB11000AF774	59	učitelj	oseba	meri	Piki	oseba	oseba: učitelj -[meri]-> oseba: Piki	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451CE6243E063AB11000AF774	59	Piki	oseba	ima lastnost	telesna temperatura	značilnost	oseba: Piki -[ima lastnost]-> značilnost: telesna temperatura	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451CF6243E063AB11000AF774	59	Piki	oseba	se pogovarja	učitelj	oseba	oseba: Piki -[se pogovarja]-> oseba: učitelj	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451D06243E063AB11000AF774	59	učitelj	oseba	pojasnjuje	Piki	oseba	oseba: učitelj -[pojasnjuje]-> oseba: Piki	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451D16243E063AB11000AF774	59	dan	čas	ima lastnost	vročina	značilnost	čas: dan -[ima lastnost]-> značilnost: vročina	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 40FAFD1451D26243E063AB11000AF774	60	učitelj	oseba	pojasnjuje	Piki	oseba	oseba: učitelj -[pojasnjuje]-> oseba: Piki	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 40FAFD1451D36243E063AB11000AF774	60	Piki	oseba	ima lastnost	vročina	bolezen	oseba: Piki -[ima lastnost]-> bolezen: vročina	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 40FAFD1451D46243E063AB11000AF774	60	učitelj	oseba	pomaga	Piki	oseba	oseba: učitelj -[pomaga]-> oseba: Piki	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 40FAFD1451D56243E063AB11000AF774	60	Piki	oseba	se ohladi	kopalna kada	predmet	oseba: Piki -[se ohladi]-> predmet: kopalna kada	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 40FAFD1451D66243E063AB11000AF774	60	Piki	oseba	se greje	peč	predmet	oseba: Piki -[se greje]-> predmet: peč	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 40FAFD1451D76243E063AB11000AF774	61	Piki	oseba	ima lastnost	čiste petke	značilnost	oseba: Piki -[ima lastnost]-> značilnost: čiste petke	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451D86243E063AB11000AF774	61	Piki	oseba	je primer	znameniti medved	značilnost	oseba: Piki -[je primer]-> značilnost: znameniti medved	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451D96243E063AB11000AF774	61	učitelj	oseba	se pripravlja	počitnice	dogodek	oseba: učitelj -[se pripravlja]-> dogodek: počitnice	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451DA6243E063AB11000AF774	61	učitelj	oseba	vzame	Piki	oseba	oseba: učitelj -[vzame]-> oseba: Piki	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451DB6243E063AB11000AF774	61	Piki	oseba	ima izkušnjo	dolgčas	čustvo	oseba: Piki -[ima izkušnjo]-> čustvo: dolgčas	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451DC6243E063AB11000AF774	61	Piki	oseba	je bil	predšolski medvedek	značilnost	oseba: Piki -[je bil]-> značilnost: predšolski medvedek	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 40FAFD1451DD6243E063AB11000AF774	62	Piki	oseba	dobi	medvedji kovček	predmet	oseba: Piki -[dobi]-> predmet: medvedji kovček	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451DE6243E063AB11000AF774	62	Piki	oseba	spravlja	medvedja prtljaso	predmet	oseba: Piki -[spravlja]-> predmet: medvedja prtljaso	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451DF6243E063AB11000AF774	62	Piki	oseba	gre na	počitnice	dogodek	oseba: Piki -[gre na]-> dogodek: počitnice	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451E06243E063AB11000AF774	62	učitelj	oseba	prepriča	govorec	oseba	oseba: učitelj -[prepriča]-> oseba: govorec	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451E16243E063AB11000AF774	62	govorec	oseba	se strinja	učitelj	oseba	oseba: govorec -[se strinja]-> oseba: učitelj	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451E26243E063AB11000AF774	62	medvedji	skupina	gre na	počitnice	dogodek	skupina: medvedji -[gre na]-> dogodek: počitnice	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 40FAFD1451E36243E063AB11000AF774	63	učitelj	oseba	zahteva	govorec	oseba	oseba: učitelj -[zahteva]-> oseba: govorec	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E46243E063AB11000AF774	63	učitelj	oseba	prosi	maček	žival	oseba: učitelj -[prosi]-> žival: maček	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E56243E063AB11000AF774	63	govorec	oseba	se upira	učitelj	oseba	oseba: govorec -[se upira]-> oseba: učitelj	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E66243E063AB11000AF774	63	učitelj	oseba	vpraša	govorec	oseba	oseba: učitelj -[vpraša]-> oseba: govorec	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E76243E063AB11000AF774	63	govorec	oseba	se spominja	zgodba o mačku	dogodek	oseba: govorec -[se spominja]-> dogodek: zgodba o mačku	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E86243E063AB11000AF774	63	govorec	oseba	odloča	maček	žival	oseba: govorec -[odloča]-> žival: maček	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 40FAFD1451E96243E063AB11000AF774	64	Piki	oseba	polni	kovček	predmet	oseba: Piki -[polni]-> predmet: kovček	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451EA6243E063AB11000AF774	64	Piki	oseba	vzame	perilo	predmet	oseba: Piki -[vzame]-> predmet: perilo	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451EB6243E063AB11000AF774	64	Piki	oseba	vzame	sandale	obutev	oseba: Piki -[vzame]-> obutev: sandale	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451EC6243E063AB11000AF774	64	Piki	oseba	vzame	plavalni obroč	pripomoček	oseba: Piki -[vzame]-> pripomoček: plavalni obroč	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451ED6243E063AB11000AF774	64	Piki	oseba	vzame	jadrnica	plovilo	oseba: Piki -[vzame]-> plovilo: jadrnica	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451EE6243E063AB11000AF774	64	Piki	oseba	obleče	mornarska majica	oblačila	oseba: Piki -[obleče]-> oblačila: mornarska majica	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451EF6243E063AB11000AF774	64	učitelj	oseba	opazuje	Piki	oseba	oseba: učitelj -[opazuje]-> oseba: Piki	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451F06243E063AB11000AF774	64	govorec	oseba	dodaja	učitelj	oseba	oseba: govorec -[dodaja]-> oseba: učitelj	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 40FAFD1451F16243E063AB11000AF774	65	učitelj	oseba	svetuje	govorec	oseba	oseba: učitelj -[svetuje]-> oseba: govorec	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F26243E063AB11000AF774	65	govorec	oseba	se strinja	učitelj	oseba	oseba: govorec -[se strinja]-> oseba: učitelj	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F36243E063AB11000AF774	65	govorec	oseba	skriva	cigarete	predmet	oseba: govorec -[skriva]-> predmet: cigarete	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F46243E063AB11000AF774	65	učitelj	oseba	vozi	avto	vozilo	oseba: učitelj -[vozi]-> vozilo: avto	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F56243E063AB11000AF774	65	Piki	oseba	sedel	sprednji sedež	prostor	oseba: Piki -[sedel]-> prostor: sprednji sedež	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F66243E063AB11000AF774	65	Piki	oseba	pozdravlja	vozniki	skupina	oseba: Piki -[pozdravlja]-> skupina: vozniki	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F76243E063AB11000AF774	65	Piki	oseba	prejema	poljubček	gesta	oseba: Piki -[prejema]-> gesta: poljubček	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F86243E063AB11000AF774	65	skupina	skupina	pripelje	morje	prostor	skupina: skupina -[pripelje]-> prostor: morje	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 40FAFD1451F96243E063AB11000AF774	66	Piki	oseba	je	zadovoljen	čustvo	oseba: Piki -[je]-> čustvo: zadovoljen	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FA6243E063AB11000AF774	66	Piki	oseba	lovi	ribe	žival	oseba: Piki -[lovi]-> žival: ribe	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FB6243E063AB11000AF774	66	Piki	oseba	se veseli	sonce	pojav	oseba: Piki -[se veseli]-> pojav: sonce	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FC6243E063AB11000AF774	66	Piki	oseba	se veseli	slana voda	pojav	oseba: Piki -[se veseli]-> pojav: slana voda	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FD6243E063AB11000AF774	66	Piki	oseba	se veseli	sladoled	hrana	oseba: Piki -[se veseli]-> hrana: sladoled	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FE6243E063AB11000AF774	66	Piki	oseba	piše	razglednica	dokument	oseba: Piki -[piše]-> dokument: razglednica	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1451FF6243E063AB11000AF774	66	Piki	oseba	podpiše	razglednica	dokument	oseba: Piki -[podpiše]-> dokument: razglednica	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1452006243E063AB11000AF774	66	Piki	oseba	obiskuje	vozniška šola	učilnica	oseba: Piki -[obiskuje]-> učilnica: vozniška šola	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1452016243E063AB11000AF774	66	Piki	oseba	opazuje	šoferske umetnine	značilnost	oseba: Piki -[opazuje]-> značilnost: šoferske umetnine	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 40FAFD1452026243E063AB11000AF774	67	Piki	oseba	vpisal v tečaj	tečaj	predmet	oseba: Piki -[vpisal v tečaj]-> predmet: tečaj	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 40FAFD1452036243E063AB11000AF774	67	Piki	oseba	uči	prometne znake	značilnost	oseba: Piki -[uči]-> značilnost: prometne znake	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 40FAFD1452046243E063AB11000AF774	67	Piki	oseba	ima učitelja	govorec	oseba	oseba: Piki -[ima učitelja]-> oseba: govorec	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 40FAFD1452056243E063AB11000AF774	67	govorec	oseba	postal učitelj	Piki	oseba	oseba: govorec -[postal učitelj]-> oseba: Piki	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 40FAFD1452066243E063AB11000AF774	67	Piki	oseba	želi postati	šofer medvedjega avtobusa	značilnost	oseba: Piki -[želi postati]-> značilnost: šofer medvedjega avtobusa	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 40FAFD1452076243E063AB11000AF774	68	Piki	oseba	risal	zvezek	predmet	oseba: Piki -[risal]-> predmet: zvezek	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD1452086243E063AB11000AF774	68	Piki	oseba	sanja	zvezek	predmet	oseba: Piki -[sanja]-> predmet: zvezek	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD1452096243E063AB11000AF774	68	Piki	oseba	opravil tečaj	prva pomoč	predmet	oseba: Piki -[opravil tečaj]-> predmet: prva pomoč	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD14520A6243E063AB11000AF774	68	Piki	oseba	vozi	avtomobilček	predmet	oseba: Piki -[vozi]-> predmet: avtomobilček	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD14520B6243E063AB11000AF774	68	Piki	oseba	ima mnenje	avtomobilček	predmet	oseba: Piki -[ima mnenje]-> predmet: avtomobilček	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD14520C6243E063AB11000AF774	68	Piki	oseba	sodeluje z	učitelj	oseba	oseba: Piki -[sodeluje z]-> oseba: učitelj	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 40FAFD14520D6243E063AB11000AF774	69	učitelj	oseba	razložil	Piki	oseba	oseba: učitelj -[razložil]-> oseba: Piki	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD14520E6243E063AB11000AF774	69	učitelj	oseba	postavil	govorec	oseba	oseba: učitelj -[postavil]-> oseba: govorec	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD14520F6243E063AB11000AF774	69	Piki	oseba	skomignil	rameni	značilnost	oseba: Piki -[skomignil]-> značilnost: rameni	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD1452106243E063AB11000AF774	69	Piki	oseba	peljala	avtodrom	prostor	oseba: Piki -[peljala]-> prostor: avtodrom	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD1452116243E063AB11000AF774	69	Piki	oseba	naučil	speljevanja in ustavljanja	značilnost	oseba: Piki -[naučil]-> značilnost: speljevanja in ustavljanja	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD1452126243E063AB11000AF774	69	Piki	oseba	menjal	prestave	značilnost	oseba: Piki -[menjal]-> značilnost: prestave	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD1452136243E063AB11000AF774	69	Piki	oseba	dodajal in odvzemal	plin	značilnost	oseba: Piki -[dodajal in odvzemal]-> značilnost: plin	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 40FAFD1452146243E063AB11000AF774	70	Piki	oseba	vozi	prometne ulice	prostor	oseba: Piki -[vozi]-> prostor: prometne ulice	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD1452156243E063AB11000AF774	70	Piki	oseba	prevozi	štiripasovnica	predmet	oseba: Piki -[prevozi]-> predmet: štiripasovnica	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD1452166243E063AB11000AF774	70	Piki	oseba	prižgal	zasenčene luči	značilnost	oseba: Piki -[prižgal]-> značilnost: zasenčene luči	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD1452176243E063AB11000AF774	70	Piki	oseba	sreča	tovornjak	predmet	oseba: Piki -[sreča]-> predmet: tovornjak	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD1452186243E063AB11000AF774	70	Piki	oseba	pobliskal	tovornjak	predmet	oseba: Piki -[pobliskal]-> predmet: tovornjak	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD1452196243E063AB11000AF774	70	Piki	oseba	se razjezi	tovornjak	predmet	oseba: Piki -[se razjezi]-> predmet: tovornjak	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 40FAFD14521A6243E063AB11000AF774	71	Piki	oseba	prižgal	dolge luči	značilnost	oseba: Piki -[prižgal]-> značilnost: dolge luči	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD14521B6243E063AB11000AF774	71	govorec	oseba	prepričal	Piki	oseba	oseba: govorec -[prepričal]-> oseba: Piki	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD14521C6243E063AB11000AF774	71	Piki	oseba	približuje se	tovornjak	predmet	oseba: Piki -[približuje se]-> predmet: tovornjak	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD14521D6243E063AB11000AF774	71	Piki	oseba	ugotovil	tovornjak	predmet	oseba: Piki -[ugotovil]-> predmet: tovornjak	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD14521E6243E063AB11000AF774	71	govorec	oseba	ugovarjal	Piki	oseba	oseba: govorec -[ugovarjal]-> oseba: Piki	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD14521F6243E063AB11000AF774	71	Piki	oseba	zagledal se	tovornjak	predmet	oseba: Piki -[zagledal se]-> predmet: tovornjak	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 40FAFD1452206243E063AB11000AF774	72	Piki	oseba	ponovil	trditev	značilnost	oseba: Piki -[ponovil]-> značilnost: trditev	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452216243E063AB11000AF774	72	Piki	oseba	razkril	resnica	značilnost	oseba: Piki -[razkril]-> značilnost: resnica	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452226243E063AB11000AF774	72	govorec	oseba	vprašal	Piki	oseba	oseba: govorec -[vprašal]-> oseba: Piki	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452236243E063AB11000AF774	72	Piki	oseba	odkril	maček	žival	oseba: Piki -[odkril]-> žival: maček	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452246243E063AB11000AF774	72	Piki	oseba	zatrobil	klik	značilnost	oseba: Piki -[zatrobil]-> značilnost: klik	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452256243E063AB11000AF774	72	maček	žival	poskočil	šok	značilnost	žival: maček -[poskočil]-> značilnost: šok	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452266243E063AB11000AF774	72	maček	žival	ucvrl	četrta brzina	značilnost	žival: maček -[ucvrl]-> značilnost: četrta brzina	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 40FAFD1452276243E063AB11000AF774	73	Piki	oseba	priglasil	izpit	predmet	oseba: Piki -[priglasil]-> predmet: izpit	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD1452286243E063AB11000AF774	73	učitelj	oseba	predsedoval	izpitna komisija	organizacija	oseba: učitelj -[predsedoval]-> organizacija: izpitna komisija	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD1452296243E063AB11000AF774	73	Piki	oseba	vozil	avto	predmet	oseba: Piki -[vozil]-> predmet: avto	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD14522A6243E063AB11000AF774	73	Piki	oseba	parkiral	avto	predmet	oseba: Piki -[parkiral]-> predmet: avto	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD14522B6243E063AB11000AF774	73	Piki	oseba	pozabil	vzvratno ogledalo	predmet	oseba: Piki -[pozabil]-> predmet: vzvratno ogledalo	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD14522C6243E063AB11000AF774	73	Piki	oseba	izvajal	ritenska vožnja	značilnost	oseba: Piki -[izvajal]-> značilnost: ritenska vožnja	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD14522D6243E063AB11000AF774	73	učitelj	oseba	seštel	kazenske točke	značilnost	oseba: učitelj -[seštel]-> značilnost: kazenske točke	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 40FAFD14522E6243E063AB11000AF774	74	Piki	oseba	nabral	točke	značilnost	oseba: Piki -[nabral]-> značilnost: točke	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD14522F6243E063AB11000AF774	74	Piki	oseba	opravil	izpit	predmet	oseba: Piki -[opravil]-> predmet: izpit	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452306243E063AB11000AF774	74	Piki	oseba	dobil	vozniško dovoljenje	dokument	oseba: Piki -[dobil]-> dokument: vozniško dovoljenje	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452316243E063AB11000AF774	74	Piki	oseba	upravlja	moterne vozilo	predmet	oseba: Piki -[upravlja]-> predmet: moterne vozilo	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452326243E063AB11000AF774	74	Piki	oseba	pogostil	steklenica ribezovega soka	predmet	oseba: Piki -[pogostil]-> predmet: steklenica ribezovega soka	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452336243E063AB11000AF774	74	Piki	oseba	vozi	avtobus	predmet	oseba: Piki -[vozi]-> predmet: avtobus	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452346243E063AB11000AF774	74	Piki	oseba	delal	voznik avtobusa	poklic	oseba: Piki -[delal]-> poklic: voznik avtobusa	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 40FAFD1452356243E063AB11000AF774	75	Piki	oseba	izbral	Josip Jupiter	oseba	oseba: Piki -[izbral]-> oseba: Josip Jupiter	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD1452366243E063AB11000AF774	75	Josip Jupiter	oseba	bil	sprevodnik	poklic	oseba: Josip Jupiter -[bil]-> poklic: sprevodnik	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD1452376243E063AB11000AF774	75	Piki	oseba	vozil	medvedji avtobus	predmet	oseba: Piki -[vozil]-> predmet: medvedji avtobus	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD1452386243E063AB11000AF774	75	Josip Jupiter	oseba	prodajal	vozni listki	predmet	oseba: Josip Jupiter -[prodajal]-> predmet: vozni listki	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD1452396243E063AB11000AF774	75	Piki	oseba	ugotovil	pomanjkanje	značilnost	oseba: Piki -[ugotovil]-> značilnost: pomanjkanje	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD14523A6243E063AB11000AF774	75	Josip Jupiter	oseba	ugotovil	pomanjkanje	značilnost	oseba: Josip Jupiter -[ugotovil]-> značilnost: pomanjkanje	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 40FAFD14523B6243E063AB11000AF774	76	Josip Jupiter	oseba	rekel	Piki	oseba	oseba: Josip Jupiter -[rekel]-> oseba: Piki	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD14523C6243E063AB11000AF774	76	Piki	oseba	odgovoril	Josip Jupiter	oseba	oseba: Piki -[odgovoril]-> oseba: Josip Jupiter	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD14523D6243E063AB11000AF774	76	Piki	oseba	predlagal	postajališča	značilnost	oseba: Piki -[predlagal]-> značilnost: postajališča	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD14523E6243E063AB11000AF774	76	avtobus	predmet	ustavil	postajališča	značilnost	predmet: avtobus -[ustavil]-> značilnost: postajališča	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD14523F6243E063AB11000AF774	76	potniki	oseba	vstopali	začetna postaja	prostor	oseba: potniki -[vstopali]-> prostor: začetna postaja	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD1452406243E063AB11000AF774	76	potniki	oseba	izstopali	končna postaja	prostor	oseba: potniki -[izstopali]-> prostor: končna postaja	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 40FAFD1452416243E063AB11000AF774	77	Piki	oseba	tožil	pomanjkanje potnikov	značilnost	oseba: Piki -[tožil]-> značilnost: pomanjkanje potnikov	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452426243E063AB11000AF774	77	Josip Jupiter	oseba	rekel	Piki	oseba	oseba: Josip Jupiter -[rekel]-> oseba: Piki	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452436243E063AB11000AF774	77	šolarji	oseba	vstopili	MEDVEDJI DOM	prostor	oseba: šolarji -[vstopili]-> prostor: MEDVEDJI DOM	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452446243E063AB11000AF774	77	šolarji	oseba	izstopili	MEDVEDJA ŠOLA	prostor	oseba: šolarji -[izstopili]-> prostor: MEDVEDJA ŠOLA	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452456243E063AB11000AF774	77	Piki	oseba	ustavil	STARI GOJZAR	prostor	oseba: Piki -[ustavil]-> prostor: STARI GOJZAR	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452466243E063AB11000AF774	77	Josip Jupiter	oseba	rekel	Benjamin	oseba	oseba: Josip Jupiter -[rekel]-> oseba: Benjamin	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452476243E063AB11000AF774	77	Benjamin	oseba	odgovoril	Josip Jupiter	oseba	oseba: Benjamin -[odgovoril]-> oseba: Josip Jupiter	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 40FAFD1452486243E063AB11000AF774	78	Josip Jupiter	oseba	govori	Benjamin	oseba	oseba: Josip Jupiter -[govori]-> oseba: Benjamin	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD1452496243E063AB11000AF774	78	Benjamin	oseba	govori	Josip Jupiter	oseba	oseba: Benjamin -[govori]-> oseba: Josip Jupiter	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524A6243E063AB11000AF774	78	Josip Jupiter	oseba	dejstvo	Benjamin	oseba	oseba: Josip Jupiter -[dejstvo]-> oseba: Benjamin	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524B6243E063AB11000AF774	78	Medvedje	oseba	dejstvo	avtobus	prostor	oseba: Medvedje -[dejstvo]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524C6243E063AB11000AF774	78	Sprevodnik	oseba	dejstvo	Marko Prvi	oseba	oseba: Sprevodnik -[dejstvo]-> oseba: Marko Prvi	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524D6243E063AB11000AF774	78	Sprevodnik	oseba	dejstvo	Marko Drugi	oseba	oseba: Sprevodnik -[dejstvo]-> oseba: Marko Drugi	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524E6243E063AB11000AF774	78	Josip Jupiter	oseba	delo	Sprevodnik	delo	oseba: Josip Jupiter -[delo]-> delo: Sprevodnik	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD14524F6243E063AB11000AF774	78	Benjamin	oseba	potovanje	avtobus	prostor	oseba: Benjamin -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD1452506243E063AB11000AF774	78	Marko Prvi	oseba	potovanje	avtobus	prostor	oseba: Marko Prvi -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD1452516243E063AB11000AF774	78	Marko Drugi	oseba	potovanje	avtobus	prostor	oseba: Marko Drugi -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 40FAFD1452526243E063AB11000AF774	79	Marko Prvi	oseba	vrže	kamen	predmet	oseba: Marko Prvi -[vrže]-> predmet: kamen	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452536243E063AB11000AF774	79	Piki	oseba	vozi	avtobus	prostor	oseba: Piki -[vozi]-> prostor: avtobus	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452546243E063AB11000AF774	79	Sprevodnik	oseba	mahajo	Marko Prvi	oseba	oseba: Sprevodnik -[mahajo]-> oseba: Marko Prvi	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452556243E063AB11000AF774	79	Sprevodnik	oseba	govori	potniki	oseba	oseba: Sprevodnik -[govori]-> oseba: potniki	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452566243E063AB11000AF774	79	Filip	oseba	govori	Sprevodnik	oseba	oseba: Filip -[govori]-> oseba: Sprevodnik	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452576243E063AB11000AF774	79	Josip Jupiter	oseba	predstavi	sprevodnik	delo	oseba: Josip Jupiter -[predstavi]-> delo: sprevodnik	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452586243E063AB11000AF774	79	Marko Prvi	oseba	pobrana	Piki	oseba	oseba: Marko Prvi -[pobrana]-> oseba: Piki	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 40FAFD1452596243E063AB11000AF774	80	Filip	oseba	govori	Josip Jupiter	oseba	oseba: Filip -[govori]-> oseba: Josip Jupiter	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525A6243E063AB11000AF774	80	Filip	oseba	počil	Josip Jupiter	oseba	oseba: Filip -[počil]-> oseba: Josip Jupiter	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525B6243E063AB11000AF774	80	Josip Jupiter	oseba	pretepa	Filip	oseba	oseba: Josip Jupiter -[pretepa]-> oseba: Filip	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525C6243E063AB11000AF774	80	Piki	oseba	vozi	avtobus	prostor	oseba: Piki -[vozi]-> prostor: avtobus	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525D6243E063AB11000AF774	80	Piki	oseba	zavrl	avtobus	prostor	oseba: Piki -[zavrl]-> prostor: avtobus	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525E6243E063AB11000AF774	80	avtobus	prostor	trči	mačji rep	predmet	prostor: avtobus -[trči]-> predmet: mačji rep	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD14525F6243E063AB11000AF774	80	mačji lastnik	oseba	prevrnil	avtobus	prostor	oseba: mačji lastnik -[prevrnil]-> prostor: avtobus	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD1452606243E063AB11000AF774	80	Piki	oseba	vidi	mačji rep	predmet	oseba: Piki -[vidi]-> predmet: mačji rep	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 40FAFD1452616243E063AB11000AF774	81	medvedje	oseba	pobirajo	avtobus	prostor	oseba: medvedje -[pobirajo]-> prostor: avtobus	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452626243E063AB11000AF774	81	sprevodnik	oseba	se prikaže	medvedje	oseba	oseba: sprevodnik -[se prikaže]-> oseba: medvedje	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452636243E063AB11000AF774	81	Piki	oseba	pomaga	tovariš	oseba	oseba: Piki -[pomaga]-> oseba: tovariš	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452646243E063AB11000AF774	81	Piki	oseba	se pognal	bojni metež	dogodek	oseba: Piki -[se pognal]-> dogodek: bojni metež	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452656243E063AB11000AF774	81	medvedje	oseba	tolče	torbice	predmet	oseba: medvedje -[tolče]-> predmet: torbice	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452666243E063AB11000AF774	81	medvedje	oseba	tolče	dežniki	predmet	oseba: medvedje -[tolče]-> predmet: dežniki	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452676243E063AB11000AF774	81	višji policijski inšpektor	oseba	prekinja	pretep	dogodek	oseba: višji policijski inšpektor -[prekinja]-> dogodek: pretep	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452686243E063AB11000AF774	81	višji policijski inšpektor	oseba	odpelje	pretepači	oseba	oseba: višji policijski inšpektor -[odpelje]-> oseba: pretepači	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD1452696243E063AB11000AF774	81	višji policijski inšpektor	oseba	izpraša	pretepači	oseba	oseba: višji policijski inšpektor -[izpraša]-> oseba: pretepači	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD14526A6243E063AB11000AF774	81	višji policijski inšpektor	oseba	naloži kazni	krivci	oseba	oseba: višji policijski inšpektor -[naloži kazni]-> oseba: krivci	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 40FAFD14526B6243E063AB11000AF774	82	Sprevodnik	oseba	odide	medvedji zapor	prostor	oseba: Sprevodnik -[odide]-> prostor: medvedji zapor	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD14526C6243E063AB11000AF774	82	Piki	oseba	preneha	voziti avtobusa	dejavnost	oseba: Piki -[preneha]-> dejavnost: voziti avtobusa	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD14526D6243E063AB11000AF774	82	Medvedje	oseba	vrnejo	škodo	značilnost	oseba: Medvedje -[vrnejo]-> značilnost: škodo	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD14526E6243E063AB11000AF774	82	Ljudje	oseba	zbirajo	prostovoljne prispevke	značilnost	oseba: Ljudje -[zbirajo]-> značilnost: prostovoljne prispevke	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD14526F6243E063AB11000AF774	82	Piki	oseba	obiskuje	govorec	oseba	oseba: Piki -[obiskuje]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452706243E063AB11000AF774	82	Sprevodnik	oseba	obiskuje	govorec	oseba	oseba: Sprevodnik -[obiskuje]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452716243E063AB11000AF774	82	Govorec	oseba	daje	Piki	oseba	oseba: Govorec -[daje]-> oseba: Piki	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452726243E063AB11000AF774	82	Govorec	oseba	daje	Sprevodnik	oseba	oseba: Govorec -[daje]-> oseba: Sprevodnik	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452736243E063AB11000AF774	82	Piki	oseba	obljublja	govorec	oseba	oseba: Piki -[obljublja]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452746243E063AB11000AF774	82	Sprevodnik	oseba	obljublja	govorec	oseba	oseba: Sprevodnik -[obljublja]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452756243E063AB11000AF774	82	Učitelj	oseba	odpre	novoletni sejem	dogodek	oseba: Učitelj -[odpre]-> dogodek: novoletni sejem	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 40FAFD1452766243E063AB11000AF774	135	Učitelj	oseba	zahteval	razlago	značilnost	oseba: Učitelj -[zahteval]-> značilnost: razlago	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD1452776243E063AB11000AF774	135	Piki	oseba	ponudil	začetek pomladi	značilnost	oseba: Piki -[ponudil]-> značilnost: začetek pomladi	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD1452786243E063AB11000AF774	135	Piki	oseba	pojasnil	prebujanje gozdnih medvedov	značilnost	oseba: Piki -[pojasnil]-> značilnost: prebujanje gozdnih medvedov	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD1452796243E063AB11000AF774	135	Piki	oseba	ponudil	Velika Medvednica	značilnost	oseba: Piki -[ponudil]-> značilnost: Velika Medvednica	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD14527A6243E063AB11000AF774	135	Učitelj	oseba	sprejel	predlog	značilnost	oseba: Učitelj -[sprejel]-> značilnost: predlog	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD14527B6243E063AB11000AF774	135	Učitelj	oseba	sestavljal	spored	značilnost	oseba: Učitelj -[sestavljal]-> značilnost: spored	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD14527C6243E063AB11000AF774	135	Učitelj	oseba	določil	pevce, igralce, plesalce in recitatorje	značilnost	oseba: Učitelj -[določil]-> značilnost: pevce, igralce, plesalce in recitatorje	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40FAFD14527D6243E063AB11000AF774	136	Piki	oseba	postal	vodja moškega pevskega zbora	značilnost	oseba: Piki -[postal]-> značilnost: vodja moškega pevskega zbora	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 40FAFD14527E6243E063AB11000AF774	136	moški pevskega zbora	skupina	vadi	pesem o dvanajstih razbojnikih	značilnost	skupina: moški pevskega zbora -[vadi]-> značilnost: pesem o dvanajstih razbojnikih	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 40FAFD14527F6243E063AB11000AF774	136	Dirigent	oseba	trkal	paličico	predmet	oseba: Dirigent -[trkal]-> predmet: paličico	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 40FAFD1452806243E063AB11000AF774	136	Dirigent	oseba	vpil	krulba	značilnost	oseba: Dirigent -[vpil]-> značilnost: krulba	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 40FAFD1452816243E063AB11000AF774	136	Velika Medvednica	dogodek	prišla	pomlad	značilnost	dogodek: Velika Medvednica -[prišla]-> značilnost: pomlad	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 40FAFD1452826243E063AB11000AF774	137	Učenci	skupina	okrasili	šolo	prostor	skupina: Učenci -[okrasili]-> prostor: šolo	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452836243E063AB11000AF774	137	Učenci	skupina	zasedli	velika šolska dvorana	prostor	skupina: Učenci -[zasedli]-> prostor: velika šolska dvorana	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452846243E063AB11000AF774	137	Piki	oseba	stal	odru	prostor	oseba: Piki -[stal]-> prostor: odru	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452856243E063AB11000AF774	137	Piki	oseba	zatrobil	medeninast rog	predmet	oseba: Piki -[zatrobil]-> predmet: medeninast rog	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452866243E063AB11000AF774	137	medvedji pevskega zbora	skupina	hiteli	odru	prostor	skupina: medvedji pevskega zbora -[hiteli]-> prostor: odru	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452876243E063AB11000AF774	137	medvedji pevskega zbora	skupina	pretegovali	se	značilnost	skupina: medvedji pevskega zbora -[pretegovali]-> značilnost: se	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452886243E063AB11000AF774	137	medvedji pevskega zbora	skupina	zbudili	zimskega spanja	značilnost	skupina: medvedji pevskega zbora -[zbudili]-> značilnost: zimskega spanja	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 40FAFD1452896243E063AB11000AF774	138	medvedji učitelj	oseba	zložil	pesem	značilnost	oseba: medvedji učitelj -[zložil]-> značilnost: pesem	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528A6243E063AB11000AF774	138	Piki	oseba	izuril	pevce	skupina	oseba: Piki -[izuril]-> skupina: pevce	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528B6243E063AB11000AF774	138	pevci	skupina	peli	pesmijo	značilnost	skupina: pevci -[peli]-> značilnost: pesmijo	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528C6243E063AB11000AF774	138	občinstvo	skupina	ploskalo	pevci	skupina	skupina: občinstvo -[ploskalo]-> skupina: pevci	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528D6243E063AB11000AF774	138	občinstvo	skupina	ploskalo	skladatelj	oseba	skupina: občinstvo -[ploskalo]-> oseba: skladatelj	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528E6243E063AB11000AF774	138	Trio Marko	skupina	nastopil	ples	značilnost	skupina: Trio Marko -[nastopil]-> značilnost: ples	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 40FAFD14528F6243E063AB11000AF774	139	medvedi	skupina	igrali	tamburice	predmet	skupina: medvedi -[igrali]-> predmet: tamburice	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 40FAFD1452906243E063AB11000AF774	139	Marki	skupina	plesali	oder	prostor	skupina: Marki -[plesali]-> prostor: oder	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 40FAFD1452916243E063AB11000AF774	139	gledalci	skupina	zahtevali	ponovitev	značilnost	skupina: gledalci -[zahtevali]-> značilnost: ponovitev	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 40FAFD1452926243E063AB11000AF774	139	Timika	oseba	nastopila	Pomlad	značilnost	oseba: Timika -[nastopila]-> značilnost: Pomlad	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 40FAFD1452936243E063AB11000AF774	139	Benjamin	oseba	nastopil	medved Domberdan	značilnost	oseba: Benjamin -[nastopil]-> značilnost: medved Domberdan	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 40FAFD1452946243E063AB11000AF774	140	Pomlad	značilnost	zaklicala	Domberdan	značilnost	značilnost: Pomlad -[zaklicala]-> značilnost: Domberdan	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD1452956243E063AB11000AF774	140	Domberdan	značilnost	odgovarjal	Pomlad	značilnost	značilnost: Domberdan -[odgovarjal]-> značilnost: Pomlad	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD1452966243E063AB11000AF774	140	Pomlad	značilnost	zlila	vodo	predmet	značilnost: Pomlad -[zlila]-> predmet: vodo	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD1452976243E063AB11000AF774	140	mladi gledalci	skupina	smehali	prizor	značilnost	skupina: mladi gledalci -[smehali]-> značilnost: prizor	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD1452986243E063AB11000AF774	140	recitatorji	skupina	nastopili	prizor	značilnost	skupina: recitatorji -[nastopili]-> značilnost: prizor	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD1452996243E063AB11000AF774	140	medvedji pevski zbor	skupina	nastopil	zaključek	značilnost	skupina: medvedji pevski zbor -[nastopil]-> značilnost: zaključek	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 40FAFD14529A6243E063AB11000AF774	141	medvedji pevski zbor	skupina	zapel	nove pesmi	značilnost	skupina: medvedji pevski zbor -[zapel]-> značilnost: nove pesmi	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD14529B6243E063AB11000AF774	141	nove pesmi	značilnost	vsebujejo	Ko medved zjutraj v šolo gre	značilnost	značilnost: nove pesmi -[vsebujejo]-> značilnost: Ko medved zjutraj v šolo gre	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD14529C6243E063AB11000AF774	141	nove pesmi	značilnost	vsebujejo	Medene lonce ližemo	značilnost	značilnost: nove pesmi -[vsebujejo]-> značilnost: Medene lonce ližemo	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD14529D6243E063AB11000AF774	141	nove pesmi	značilnost	vsebujejo	Medvedje hrabri smo gasilci	značilnost	značilnost: nove pesmi -[vsebujejo]-> značilnost: Medvedje hrabri smo gasilci	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD14529E6243E063AB11000AF774	141	nove pesmi	značilnost	vsebujejo	Pomald -medvedji letni čas	značilnost	značilnost: nove pesmi -[vsebujejo]-> značilnost: Pomald -medvedji letni čas	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD14529F6243E063AB11000AF774	141	medvedi	skupina	prejeli	minihrenovko	predmet	skupina: medvedi -[prejeli]-> predmet: minihrenovko	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD1452A06243E063AB11000AF774	141	medvedi	skupina	prejeli	makismed	predmet	skupina: medvedi -[prejeli]-> predmet: makismed	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD1452A16243E063AB11000AF774	141	učiteljeva mama	oseba	pripravila	slavnostno kosilo	značilnost	oseba: učiteljeva mama -[pripravila]-> značilnost: slavnostno kosilo	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD1452A26243E063AB11000AF774	141	učitelj	oseba	predlagal	potovanje v Pariz	značilnost	oseba: učitelj -[predlagal]-> značilnost: potovanje v Pariz	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 40FAFD1452A36243E063AB11000AF774	142	učitelj	oseba	ponovil	Pariz	prostor	oseba: učitelj -[ponovil]-> prostor: Pariz	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A46243E063AB11000AF774	142	Piki	oseba	bi obiskal	Žužuja	prostor	oseba: Piki -[bi obiskal]-> prostor: Žužuja	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A56243E063AB11000AF774	142	učitelj	oseba	predlagal	potovanje	značilnost	oseba: učitelj -[predlagal]-> značilnost: potovanje	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A66243E063AB11000AF774	142	učitelj	oseba	predlagal	severni tečaj	značilnost	oseba: učitelj -[predlagal]-> značilnost: severni tečaj	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A76243E063AB11000AF774	142	govorec	oseba	vprašal	učitelj	oseba	oseba: govorec -[vprašal]-> oseba: učitelj	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A86243E063AB11000AF774	142	govorec	oseba	rekel	učitelj	oseba	oseba: govorec -[rekel]-> oseba: učitelj	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452A96243E063AB11000AF774	142	govorec	oseba	vprašal	učitelj	oseba	oseba: govorec -[vprašal]-> oseba: učitelj	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452AA6243E063AB11000AF774	142	učitelj	oseba	odgovoril	avtom	predmet	oseba: učitelj -[odgovoril]-> predmet: avtom	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 40FAFD1452AB6243E063AB11000AF774	143	učitelj	oseba	predlagal	severni tečaj	prostor	oseba: učitelj -[predlagal]-> prostor: severni tečaj	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452AC6243E063AB11000AF774	143	Piki	oseba	bi rad videl	severne medvede	žival	oseba: Piki -[bi rad videl]-> žival: severne medvede	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452AD6243E063AB11000AF774	143	Piki	oseba	bi rad videl	pingvine	žival	oseba: Piki -[bi rad videl]-> žival: pingvine	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452AE6243E063AB11000AF774	143	Piki	oseba	bi rad videl	mrože	žival	oseba: Piki -[bi rad videl]-> žival: mrože	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452AF6243E063AB11000AF774	143	učitelj	oseba	predlagal	avtom	predmet	oseba: učitelj -[predlagal]-> predmet: avtom	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452B06243E063AB11000AF774	143	učitelj	oseba	predlagal	Eskimi	etnična skupina	oseba: učitelj -[predlagal]-> etnična skupina: Eskimi	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452B16243E063AB11000AF774	143	učitelj	oseba	predlagal	pasja vprega	predmet	oseba: učitelj -[predlagal]-> predmet: pasja vprega	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 40FAFD1452B26243E063AB11000AF774	144	Piki	oseba	ima željo	severni medvedi	žival	oseba: Piki -[ima željo]-> žival: severni medvedi	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B36243E063AB11000AF774	144	Piki	oseba	ima željo	levi	žival	oseba: Piki -[ima željo]-> žival: levi	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B46243E063AB11000AF774	144	Piki	oseba	ima željo	tigri	žival	oseba: Piki -[ima željo]-> žival: tigri	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B56243E063AB11000AF774	144	Piki	oseba	ima željo	sloni	žival	oseba: Piki -[ima željo]-> žival: sloni	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B66243E063AB11000AF774	144	Piki	oseba	ima željo	antilope	žival	oseba: Piki -[ima željo]-> žival: antilope	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B76243E063AB11000AF774	144	Piki	oseba	ima željo	žirafe	žival	oseba: Piki -[ima željo]-> žival: žirafe	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B86243E063AB11000AF774	144	Piki	oseba	ima željo	krokodili	žival	oseba: Piki -[ima željo]-> žival: krokodili	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452B96243E063AB11000AF774	144	Piki	oseba	ima željo	zmaji	mitološka bitja	oseba: Piki -[ima željo]-> mitološka bitja: zmaji	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452BA6243E063AB11000AF774	144	učitelj	oseba	se pogovarja	Piki	oseba	oseba: učitelj -[se pogovarja]-> oseba: Piki	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452BB6243E063AB11000AF774	144	zmaji	mitološka bitja	se pojavljajo	pravljica	literarna vrsta	mitološka bitja: zmaji -[se pojavljajo]-> literarna vrsta: pravljica	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 40FAFD1452BC6243E063AB11000AF774	145	učitelj	oseba	govori	pravljica	literarna vrsta	oseba: učitelj -[govori]-> literarna vrsta: pravljica	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452BD6243E063AB11000AF774	145	učitelj	oseba	se pogovarja	govorec	oseba	oseba: učitelj -[se pogovarja]-> oseba: govorec	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452BE6243E063AB11000AF774	145	govorec	oseba	govori	pravljica	literarna vrsta	oseba: govorec -[govori]-> literarna vrsta: pravljica	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452BF6243E063AB11000AF774	145	govorec	oseba	predlaga	peš	način potovanja	oseba: govorec -[predlaga]-> način potovanja: peš	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C06243E063AB11000AF774	145	učitelj	oseba	želi	Pariz	mesto	oseba: učitelj -[želi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C16243E063AB11000AF774	145	Piki	oseba	želi	Pariz	mesto	oseba: Piki -[želi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C26243E063AB11000AF774	145	govorec	oseba	trdi	Pariz	mesto	oseba: govorec -[trdi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C36243E063AB11000AF774	145	govorec	oseba	trdi	severni tečaj	geografska lokacija	oseba: govorec -[trdi]-> geografska lokacija: severni tečaj	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C46243E063AB11000AF774	145	govorec	oseba	trdi	Afrika	kontinent	oseba: govorec -[trdi]-> kontinent: Afrika	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 40FAFD1452C56243E063AB11000AF774	146	govorec	oseba	misli	resno	značilnost	oseba: govorec -[misli]-> značilnost: resno	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452C66243E063AB11000AF774	146	učitelj	oseba	govori	govorec	oseba	oseba: učitelj -[govori]-> oseba: govorec	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452C76243E063AB11000AF774	146	učitelj	oseba	prosi	govorec	oseba	oseba: učitelj -[prosi]-> oseba: govorec	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452C86243E063AB11000AF774	146	govorec	oseba	predlaga	živalski vrt	prostor	oseba: govorec -[predlaga]-> prostor: živalski vrt	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452C96243E063AB11000AF774	146	govorec	oseba	obljubljajo	učitelj	oseba	oseba: govorec -[obljubljajo]-> oseba: učitelj	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452CA6243E063AB11000AF774	146	govorec	oseba	vozi	učitelj	oseba	oseba: govorec -[vozi]-> oseba: učitelj	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452CB6243E063AB11000AF774	146	učitelj	oseba	pripravlja	stari kruh	predmet	oseba: učitelj -[pripravlja]-> predmet: stari kruh	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 40FAFD1452CC6243E063AB11000AF774	147	učitelj	oseba	govori	govorec	oseba	oseba: učitelj -[govori]-> oseba: govorec	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452CD6243E063AB11000AF774	147	učitelj	oseba	pogovarja se	Piki	oseba	oseba: učitelj -[pogovarja se]-> oseba: Piki	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452CE6243E063AB11000AF774	147	govorec	oseba	pogovarja se	učitelj	oseba	oseba: govorec -[pogovarja se]-> oseba: učitelj	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452CF6243E063AB11000AF774	147	učitelj	oseba	potrdi	živalski vrt	prostor	oseba: učitelj -[potrdi]-> prostor: živalski vrt	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D06243E063AB11000AF774	147	govorec	oseba	obljubljajo	učitelj	oseba	oseba: govorec -[obljubljajo]-> oseba: učitelj	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D16243E063AB11000AF774	147	govorec	oseba	obiskuje	živalski vrt	prostor	oseba: govorec -[obiskuje]-> prostor: živalski vrt	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D26243E063AB11000AF774	147	govorec	oseba	potuje	severni tečaj	geografska lokacija	oseba: govorec -[potuje]-> geografska lokacija: severni tečaj	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D36243E063AB11000AF774	147	govorec	oseba	obiskuje	Rožnik	prostor	oseba: govorec -[obiskuje]-> prostor: Rožnik	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D46243E063AB11000AF774	147	govorec	oseba	opazuje	opice	žival	oseba: govorec -[opazuje]-> žival: opice	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D56243E063AB11000AF774	147	govorec	oseba	vozi	sane	predmet	oseba: govorec -[vozi]-> predmet: sane	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 40FAFD1452D66243E063AB11000AF774	148	čarovniki	značilnost	so	učenci	značilnost	značilnost: čarovniki -[so]-> značilnost: učenci	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 40FAFD1452D76243E063AB11000AF774	148	učenci	značilnost	so	kljukci	značilnost	značilnost: učenci -[so]-> značilnost: kljukci	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 40FAFD1452D86243E063AB11000AF774	148	kljukci	značilnost	so	mile jere	značilnost	značilnost: kljukci -[so]-> značilnost: mile jere	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 40FAFD1452D96243E063AB11000AF774	148	mile jere	značilnost	so	radovedneži	značilnost	značilnost: mile jere -[so]-> značilnost: radovedneži	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 40FAFD1452DA6243E063AB11000AF774	148	radovedneži	značilnost	so	poredneži	značilnost	značilnost: radovedneži -[so]-> značilnost: poredneži	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 40FAFD1452DB6243E063AB11000AF774	109	Piki in učitelj	skupina	znosita	zabojčke, lončke, prst in vrečke s čebulicami	predmet	skupina: Piki in učitelj -[znosita]-> predmet: zabojčke, lončke, prst in vrečke s čebulicami	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 40FAFD1452DC6243E063AB11000AF774	109	učitelj	oseba	svetuje	Piki	oseba	oseba: učitelj -[svetuje]-> oseba: Piki	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 40FAFD1452DD6243E063AB11000AF774	109	Piki	oseba	sadita	čebulice	predmet	oseba: Piki -[sadita]-> predmet: čebulice	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 40FAFD1452DE6243E063AB11000AF774	109	Piki	oseba	pričakuje	mamina veselje	značilnost	oseba: Piki -[pričakuje]-> značilnost: mamina veselje	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 40FAFD1452DF6243E063AB11000AF774	109	učitelj	oseba	upajo	mamina veselje	značilnost	oseba: učitelj -[upajo]-> značilnost: mamina veselje	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.

> Output is truncated to 256 KB.

SQL Property Graph that we are creating will be based on two tables: **GRAPH_ENTITIES_STORY** and **GRAPH_RELATIONS_STORY**. Both will retrieve its contents from the staging table **GRAPH_RELATIONS_STG** created in the previous step.

SQL Property Graph that we are creating will be based on two tables: GRAPH_ENTITIES_STORY and GRAPH_RELATIONS_STORY. Both will retrieve its contents from the staging table GRAPH_RELATIONS_STG created in the previous step.

```sql
BEGIN
  ---------------------------------------------------------------------------
  -- Drop and recreate GRAPH_ENTITIES_STORY
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE GRAPH_ENTITIES_STORY PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF; -- ignore "table or view does not exist"
  END;

  EXECUTE IMMEDIATE '
    CREATE TABLE GRAPH_ENTITIES_STORY (
      ID           NUMBER GENERATED ALWAYS AS IDENTITY (START WITH 1 CACHE 20) NOT NULL,
      ENTITY_NAME  VARCHAR2(250),
      ENTITY_TYPE  VARCHAR2(250)
    )
  ';

  ---------------------------------------------------------------------------
  -- Drop and recreate GRAPH_RELATIONS_STORY
  ---------------------------------------------------------------------------
  BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE GRAPH_RELATIONS_STORY PURGE';
  EXCEPTION
    WHEN OTHERS THEN
      IF SQLCODE != -942 THEN 
        RAISE; 
      END IF; -- ignore "table or view does not exist"
  END;

  EXECUTE IMMEDIATE '
    CREATE TABLE GRAPH_RELATIONS_STORY (
      ID          NUMBER GENERATED ALWAYS AS IDENTITY (START WITH 1 CACHE 20) NOT NULL,
      CHUNK_ID    NUMBER,
      HEAD_ID     NUMBER,
      TAIL_ID     NUMBER,
      RELATION    VARCHAR2(256) NOT NULL,
      TEXT        VARCHAR2(512),
      CHUNK_DATA  VARCHAR2(4000)
    )
  ';
END;
/
```

> PL/SQL procedure successfully completed.

```sql
INSERT INTO GRAPH_ENTITIES_STORY (ENTITY_NAME, ENTITY_TYPE) 
SELECT ENTITY_NAME, ENTITY_TYPE FROM (
    SELECT HEAD AS ENTITY_NAME, head_type AS ENTITY_TYPE
    FROM GRAPH_RELATIONS_STG
    UNION
    SELECT TAIL AS ENTITY_NAME, TAIL_type AS ENTITY_TYPE
    FROM GRAPH_RELATIONS_STG);

COMMIT;
```

> Query executed successfully. Affected rows : 679

```sql
SELECT * FROM GRAPH_ENTITIES_STORY;
```

> ID	ENTITY_NAME	ENTITY_TYPE
> 1	Afrika	kontinent
> 2	Benjamin	oseba
> 3	Benjamin in Filip	skupina
> 4	Berenson	oseba
> 5	Boksali	oseba
> 6	Debeli Bongo	oseba
> 7	Dirigent	oseba
> 8	Dolgi Jakec	oseba
> 9	Domberdan	značilnost
> 10	Dvorana smrti	prostor
> 11	Eskimi	etnična skupina
> 12	Filip	oseba
> 13	Filip in Benjamin	skupina
> 14	Floki	oseba
> 15	Flokijeva knjiga	predmet
> 16	Govorec	oseba
> 17	Hiša strahov	prostor
> 18	Josip Jupiter	oseba
> 19	Jupiter	oseba
> 20	Ko medved zjutraj v šolo gre	značilnost
> 21	Koračnica palčkov	glasba
> 22	Lapasti Kljukec	oseba
> 23	Ljubljana	prostor
> 24	Ljudje	oseba
> 25	Lovikrogla	oseba
> 26	MEDVEDJA ŠOLA	prostor
> 27	MEDVEDJI DOM	prostor
> 28	Mali Makec	oseba
> 29	Marki	skupina
> 30	Marko	oseba
> 31	Marko Drugi	oseba
> 32	Marko Prvi	oseba
> 33	Marmeladov	oseba
> 34	Medene lonce ližemo	značilnost
> 35	Medolizis	oseba
> 36	Medvedja šola	prostor
> 37	Medvedje	oseba
> 38	Medvedje hrabri smo gasilci	značilnost
> 39	Mečkovič	oseba
> 40	Na planincah luštno biti	pesem
> 41	Nemi Lukec	oseba
> 42	POGUMNI PADALEC	nagrada
> 43	POŽAR V NBOTIČNIKU	naziv
> 44	PP	značilnost
> 45	Pariz	mesto
> 46	Pariz	prostor
> 47	Pastirica žgance kuha, notri pade ena muha	pesem
> 48	Piki	oseba
> 49	Piki	značilnost
> 50	Piki Jakob	oseba
> 51	Piki in Jupiter	oseba
> 52	Piki in učitelj	skupina
> 53	Piki je Francoz	značilnost
> 54	Piki ne mara francoske solate	značilnost
> 55	Piki padalec	oseba
> 56	Piki vrtnar	oseba
> 57	Pikijev kralj	predmet
> 58	Pikijeva knjižica	predmet
> 59	Pikijeva predloga	predloga
> 60	Pikijeva zmaga	dogodek
> 61	Polkovnik	oseba
> 62	Pomald -medvedji letni čas	značilnost
> 63	Pomlad	značilnost
> 64	Poveljnik	oseba
> 65	Rožnik	prostor
> 66	STARI GOJZAR	prostor
> 67	Sora	prostor
> 68	Sprevodnik	delo
> 69	Sprevodnik	oseba
> 70	Stari Marko	oseba
> 71	Suhi Grintež	oseba
> 72	Tedi	oseba
> 73	Timika	oseba
> 74	Trio Marko	skupina
> 75	Učenci	skupina
> 76	Učitelj	oseba
> 77	Učiteljeva mama	oseba
> 78	Velika Medvednica	dogodek
> 79	Velika Medvednica	značilnost
> 80	antilope	žival
> 81	aspirin	zdravilo
> 82	avto	predmet
> 83	avto	vozilo
> 84	avtobus	predmet
> 85	avtobus	prostor
> 86	avtodrom	prostor
> 87	avtom	predmet
> 88	avtomobilček	predmet
> 89	babi	oseba
> 90	balinčki	predmet
> 91	balkon	prostor
> 92	balkoni	prostor
> 93	banjo	predmet
> 94	barko	risba
> 95	bele figure	figurka
> 96	beli krokusi	predmet
> 97	beli mehurčki	predmet
> 98	berezov gaj	prostor
> 99	blok	prostor
> 100	blokflavta	predmet
> 101	bojni metež	dogodek
> 102	bolniška sestra	oseba
> 103	branje spominskih knjig	dejanje
> 104	cev	predmet
> 105	cigarete	predmet
> 106	cilj	prostor
> 107	cirkus	prostor
> 108	cirkus bežigrad	prostor
> 109	curek	značilnost
> 110	cviljenje	značilnost
> 111	dan	čas
> 112	dan otvoritve	dogodek
> 113	ded	oseba
> 114	deska	predmet
> 115	deček	oseba
> 116	dežniki	predmet
> 117	direktor	oseba
> 118	dneve	značilnost
> 119	dnevi	čas
> 120	dnevna soba	prostor
> 121	dolge luči	značilnost
> 122	dolgčas	čustvo
> 123	domov	prostor
> 124	dresura tigrov	dogodek
> 125	drevesa	predmet
> 126	drgniti parket	dejanje
> 127	drugo nadstropje	prostor
> 128	družina	skupina
> 129	en dinar	predmet
> 130	fantek	oseba
> 131	fantje	skupina
> 132	fikus	predmet
> 133	film o padalcih	film
> 134	francoska solata	jedi
> 135	francosko	jezik
> 136	gasilce	skupina
> 137	gasilci	skupina
> 138	gasilska akcija	dogodek
> 139	gasilska sirena	predmet
> 140	gasilske značke	predmet
> 141	gasilski avto	avto
> 142	gasilski miting	dogodek
> 143	gledalci	skupina
> 144	gnila jajca in paradižnike	predmet
> 145	godba	skupina
> 146	gorčica	značilnost
> 147	gospa	oseba
> 148	gostija	dogodek
> 149	gostolij	značilnost
> 150	govorec	oseba
> 151	greben	prostor
> 152	grm forsicije	predmet
> 153	grmenje in bliskanje	značilnost
> 154	gum gasilskega avta	del
> 155	helikopter	predmet
> 156	hiša	prostor
> 157	hiša strahov	prostor
> 158	hlačnico	predmet
> 159	hodnik	prostor
> 160	hruško	predmet
> 161	hud	značilnost
> 162	hudi tiger	žival
> 163	ime	značilnost
> 164	imenitne jedi	značilnost
> 165	izkopavanje	dejanje
> 166	izložba	prostor
> 167	izobražen	značilnost
> 168	izpit	predmet
> 169	izpitna komisija	organizacija
> 170	jadrnica	plovilo
> 171	jed je strup	značilnost
> 172	južno gričevje	prostor
> 173	kabina	predmet
> 174	kabino	predmet
> 175	kamen	predmet
> 176	kanarček	žival
> 177	kariraste čepice	predmet
> 178	kazenske točke	značilnost
> 179	kletka	prostor
> 180	kletka z zelenima papagajema	predmet
> 181	klik	značilnost
> 182	kljukci	značilnost
> 183	klop	predmet
> 184	klovni	oseba
> 185	klovni	predmet
> 186	kmet	predmet
> 187	knjiga	predmet
> 188	kolera	zdravstvena stanja
> 189	končna postaja	prostor
> 190	kopalna kada	predmet
> 191	kopalnica	prostor
> 192	kovinska paličica	predmet
> 193	kovček	predmet
> 194	kraj požara	prostor
> 195	kralj	predmet
> 196	kraljica	figurka
> 197	kraljica	predmet
> 198	kremplje	predmet
> 199	krivci	oseba
> 200	krogla	predmet
> 201	krogle	predmet
> 202	krojne pole	orodje
> 203	krokodili	žival
> 204	krulba	značilnost
> 205	kuhelmuc	oseba
> 206	kuhinja	prostor
> 207	kumarice	značilnost
> 208	ladjice	predmet
> 209	lajanje	značilnost
> 210	lestve	predmet
> 211	leteči medved	značilnost
> 212	lev	žival
> 213	lev in tigri	žival
> 214	levi	žival
> 215	lista	predmet
> 216	listek	značilnost
> 217	ljudje	oseba
> 218	lonček za čaj	predmet
> 219	majonezo	značilnost
> 220	makismed	predmet
> 221	mama	oseba
> 222	mamina veselje	značilnost
> 223	mamina vprašanje	značilnost
> 224	manj navdušen	značilnost
> 225	matador	oseba
> 226	maček	žival
> 227	maček na metli	predmet
> 228	mačji lastnik	oseba
> 229	mačji rep	predmet
> 230	mačka	žival
> 231	mačke	žival
> 232	mačke ne žvižgajo	značilnost
> 233	med	značilnost
> 234	medeninast rog	predmet
> 235	medved	oseba
> 236	medved Domberdan	značilnost
> 237	medved Piki	oseba
> 238	medvedbudilka	značilnost
> 239	medvedek	predmet
> 240	medvedi	oseba
> 241	medvedi	skupina
> 242	medvedi v Parizu	oseba
> 243	medvedja kočija	predmet
> 244	medvedja mamica	oseba
> 245	medvedja prtljaso	predmet
> 246	medvedja šola	prostor
> 247	medvedje	oseba
> 248	medvedje	osebe
> 249	medvedje	skupina
> 250	medvedje	žival
> 251	medvedji	oseba
> 252	medvedji	skupina
> 253	medvedji avtobus	predmet
> 254	medvedji gasilci	skupina
> 255	medvedji jezik	jezik
> 256	medvedji kovček	predmet
> 257	medvedji pevskega zbora	skupina
> 258	medvedji pevski zbor	skupina
> 259	medvedji prijatelji	oseba
> 260	medvedji učitelj	oseba
> 261	medvedji zapor	prostor
> 262	medvedji šola	prostor
> 263	medvedji športniki	oseba
> 264	medvedki	predmet
> 265	mehek	značilnost
> 266	mehki travnik	prostor
> 267	metro	predmet
> 268	mijavkanje	značilnost
> 269	mile jere	značilnost
> 270	minihrenovko	predmet
> 271	minus v vedenju	dejanje
> 272	mir	značilnost
> 273	mizo	predmet
> 274	mladi gledalci	skupina
> 275	modre hijacinte	predmet
> 276	modrost	značilnost
> 277	modrost Marka Prvega	značilnost
> 278	morje	prostor
> 279	mornarska majica	oblačila
> 280	morska trava	material
> 281	moterne vozilo	predmet
> 282	motorizacijo	značilnost
> 283	motorno brizgalno	predmet
> 284	močvirni predeli	prostor
> 285	moški	oseba
> 286	moški pevskega zbora	skupina
> 287	moštvo	skupina
> 288	možakar	oseba
> 289	mračen predor	prostor
> 290	mrože	žival
> 291	mulasto	značilnost
> 292	nageljnov	vsebina
> 293	največji tiger	žival
> 294	naloga	predmet
> 295	napis	značilnost
> 296	navdušen	značilnost
> 297	ne bom jedel	značilnost
> 298	ne maram čudnih jedi	značilnost
> 299	nebotičnik	zgradba
> 300	nedelja popoldne	čas
> 301	nekaj	pojem
> 302	nekaj	predmet
> 303	nesposobnost zaspati	značilnost
> 304	nevarni predor	prostor
> 305	neznani prejemnik	oseba
> 306	neznanje	značilnost
> 307	ni potrebno obvestiti	značilnost
> 308	nove pesmi	značilnost
> 309	novoletni sejem	dogodek
> 310	ob treh	čas
> 311	obiskovalci	oseba
> 312	obkladke	predmet
> 313	obroč	predmet
> 314	občinstvo	oseba
> 315	občinstvo	skupina
> 316	oder	prostor
> 317	odlično izurjeno	značilnost
> 318	odprto okno	predmet
> 319	odru	prostor
> 320	odskok	dejanje
> 321	odskočišče	prostor
> 322	odvijanje cevi	dejanje
> 323	ogledala	predmet
> 324	ognjeni krst	izkušnja
> 325	ogroženi prebivalci	skupina
> 326	ohladitev	značilnost
> 327	okna	predmet
> 328	okrog kletke	prostor
> 329	omara	predmet
> 330	opice	žival
> 331	oprema	predmet
> 332	otrok	oseba
> 333	očeta	oseba
> 334	padala	predmet
> 335	padalci	oseba
> 336	padalec	oseba
> 337	padalec	poklic
> 338	padalo	predmet
> 339	padalski polkovnik	poklic
> 340	padalski telovniki	oprema
> 341	padalsko društvo	organizacija
> 342	padalstvom	šport
> 343	paličico	predmet
> 344	parfum	značilnost
> 345	pasja vprega	predmet
> 346	paviljon s skrivnostnim napisom	prostor
> 347	paviljon z ogledali	prostor
> 348	pentlja	značilnost
> 349	perilo	predmet
> 350	pes	žival
> 351	pesem	značilnost
> 352	pesem o dvanajstih razbojnikih	značilnost
> 353	pesmijo	značilnost
> 354	pevce	skupina
> 355	pevce, igralce, plesalce in recitatorje	značilnost
> 356	pevci	skupina
> 357	peč	predmet
> 358	peš	način potovanja
> 359	pingvine	žival
> 360	pisanje	dejanje
> 361	pismo	dokument
> 362	plavalni obroč	pripomoček
> 363	ples	značilnost
> 364	plin	značilnost
> 365	plišasti medvedek	značilnost
> 366	pogasitev požara	dogodek
> 367	pokrovko	predmet
> 368	polet	vaja
> 369	polica	prostor
> 370	poljubček	gesta
> 371	polkovnik	oseba
> 372	pomanjkanje	značilnost
> 373	pomanjkanje potnikov	značilnost
> 374	pomlad	značilnost
> 375	pomlad	čas
> 376	pomočnik	poklic
> 377	ponjavo	prostor
> 378	ponovitev	značilnost
> 379	poredneži	značilnost
> 380	posaditev čebulic	dogodek
> 381	postajališča	značilnost
> 382	postavljanje lestev	dejanje
> 383	postelja	predmet
> 384	poten	značilnost
> 385	poteza	predmet
> 386	potniki	oseba
> 387	potovanje	značilnost
> 388	potovanje v Pariz	značilnost
> 389	povelja	ukaz
> 390	poveljnik	oseba
> 391	pozabljen napis	značilnost
> 392	počitnice	dogodek
> 393	pošta	prostor
> 394	poštar	oseba
> 395	poštna skrinjica	predmet
> 396	pravi gasilci	značilnost
> 397	pravilnost tablic	značilnost
> 398	pravljica	literarna vrsta
> 399	pravljične hišice	vsebina
> 400	praznika	značilnost
> 401	prebrisan	značilnost
> 402	prebujanje gozdnih medvedov	značilnost
> 403	predlog	značilnost
> 404	predloge	značilnost
> 405	predori	prostor
> 406	predstava	dogodek
> 407	predšolski medvedek	značilnost
> 408	preizkušanje znanja	značilnost
> 409	preostali tiger	žival
> 410	preskakovanje ovir	dejanje
> 411	prestave	značilnost
> 412	pretep	dogodek
> 413	pretepači	oseba
> 414	pripovedovalec	oseba
> 415	pripravniki	skupina
> 416	prireditev	dogodek
> 417	prizor	značilnost
> 418	proga	prostor
> 419	prometne ulice	prostor
> 420	prometne znake	značilnost
> 421	prosti vstop	značilnost
> 422	prostor	prostor
> 423	prostovoljne prispevke	značilnost
> 424	prst	predmet
> 425	prva pomoč	predmet
> 426	prva vaja	dogodek
> 427	ptičke	žival
> 428	ptički	žival
> 429	pusto planjavo	prostor
> 430	rada	značilnost
> 431	radovedneži	značilnost
> 432	rameni	značilnost
> 433	razglednica	dokument
> 434	razlago	značilnost
> 435	razmetane učiteljeve igrače	predmet
> 436	razred	prostor
> 437	rdeč nagelj	predmet
> 438	rdeči tulipani	predmet
> 439	recitatorji	skupina
> 440	rep črnega leva	predmet
> 441	resnica	značilnost
> 442	resno	značilnost
> 443	ribe	žival
> 444	ribnik	prostor
> 445	ritenska vožnja	značilnost
> 446	rože	predmet
> 447	rožnate hijacinte	predmet
> 448	rumeni krokusi	predmet
> 449	ruto	predmet
> 450	rvav in bel pliš	značilnost
> 451	saditev cvetic	aktivnost
> 452	saditev rož	aktivnost
> 453	saditev čebulic	aktivnost
> 454	sami doma	značilnost
> 455	sandale	obutev
> 456	sane	predmet
> 457	se	značilnost
> 458	sebe	oseba
> 459	sejmišče in zabavišče	prostor
> 460	severne medvede	žival
> 461	severni medvedi	žival
> 462	severni tečaj	geografska lokacija
> 463	severni tečaj	prostor
> 464	severni tečaj	značilnost
> 465	situcija	značilnost
> 466	skladatelj	oseba
> 467	skok s višine	dejanje
> 468	skrbnik potnikov	poklic
> 469	skupina	skupina
> 470	slabost	značilnost
> 471	sladoled	hrana
> 472	slana voda	pojav
> 473	slavnostno kosilo	značilnost
> 474	sloni	žival
> 475	smrt	pojem
> 476	smrt	predmet
> 477	sodelovanje z Pikijem	dejanje
> 478	sonce	pojav
> 479	sončarica	zdravstvena stanja
> 480	spalnica	prostor
> 481	speljevanja in ustavljanja	značilnost
> 482	spominska knjiga	predmet
> 483	spominske knjige	predmet
> 484	spomladanski kros	dogodek
> 485	spored	značilnost
> 486	sprednji sedež	prostor
> 487	sprevodnik	delo
> 488	sprevodnik	oseba
> 489	sprevodnik	poklic
> 490	stara gospa	oseba
> 491	stari Marko	oseba
> 492	stari grad	prostor
> 493	stari kruh	predmet
> 494	stavek	vsebina
> 495	stavka	predmet
> 496	steklenica ribezovega soka	predmet
> 497	stenska lekarnica	prostor
> 498	stol	predmet
> 499	stopnišče	prostor
> 500	svoj kralj	figurka
> 501	svojem mnenju	značilnost
> 502	tableto	predmet
> 503	tablice	predmet
> 504	taco	dejanje
> 505	tamburice	predmet
> 506	tekanje	dejanje
> 507	tekmovalci	oseba
> 508	tekmovali	dogodek
> 509	telesna temperatura	značilnost
> 510	temna goščava	prostor
> 511	tečaj	predmet
> 512	težava	značilnost
> 513	tiger	žival
> 514	tigri	žival
> 515	tišina	značilnost
> 516	toplomer	orodje
> 517	torbice	predmet
> 518	tovariš	oseba
> 519	tovornjak	predmet
> 520	točke	značilnost
> 521	trava za blokom	prostor
> 522	trditev	značilnost
> 523	trdnjava	figurka
> 524	trdoto papagajevega kljuna	značilnost
> 525	trgovina	prostor
> 526	trobent	predmet
> 527	trobenta	predmet
> 528	trobentanje	zvočni signal
> 529	uho	predmet
> 530	umetnik	oseba
> 531	ura	dogodek
> 532	ustaviti tekmovanje	dogodek
> 533	učenci	skupina
> 534	učenci	značilnost
> 535	učitelj	oseba
> 536	učitelj in Piki	oseba
> 537	učitelj in Piki	skupina
> 538	učitelj in medvedje	skupina
> 539	učiteljev oče	oseba
> 540	učiteljeva mama	oseba
> 541	učiteljeva skrb	značilnost
> 542	učiteljeve figure	predmet
> 543	učiteljevo mnenje	značilnost
> 544	učiteljevo trditev	značilnost
> 545	uši	značilnost
> 546	v prst	prostor
> 547	vadbeni urnik	dokument
> 548	vajanje	dejanje
> 549	vaje	dejanje
> 550	vata	material
> 551	velika šolska dvorana	prostor
> 552	velikansko hruško	predmet
> 553	veliko hruško	predmet
> 554	verze	vsebina
> 555	verzi	vsebina
> 556	veter	element
> 557	večer	čas
> 558	veža	prostor
> 559	višji gasilec	poklic
> 560	višji policijski inšpektor	oseba
> 561	vlakec	predmet
> 562	vodeni krst	izkušnja
> 563	vodja moškega pevskega zbora	značilnost
> 564	vodo	predmet
> 565	vodogrelec	predmet
> 566	voziti avtobusa	dejavnost
> 567	vozni listki	predmet
> 568	voznik avtobusa	poklic
> 569	vozniki	skupina
> 570	vozniška šola	učilnica
> 571	vozniško dovoljenje	dokument
> 572	vožnja z žičnico	aktivnost
> 573	vrata	predmet
> 574	vrečica	predmet
> 575	vrečice s čebulicami	predmet
> 576	vrh	prostor
> 577	vrhnja nadstropja	prostor
> 578	vroče vaje	aktivnost
> 579	vroči lipov čaj	napitek
> 580	vročina	bolezen
> 581	vročina	značilnost
> 582	vročino	zdravstvena stanja
> 583	vrsto	skupina
> 584	vrtnarija	prostor
> 585	vrtnarja	oseba
> 586	vrtnarski krožek	skupina
> 587	vrtnarski vajenec	poklic
> 588	vrtnice	vsebina
> 589	vrtoglavica	vaja
> 590	vrvi	predmet
> 591	vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba	predmet
> 592	vrvohodec	vloga
> 593	vzpon	značilnost
> 594	vzvratno ogledalo	predmet
> 595	zaboj za igrače	prostor
> 596	zabojček z napisom: rumeni tulipan	prostor
> 597	zabojčke	predmet
> 598	zabojčke, lončke, prst in vrečke s čebulicami	predmet
> 599	zabojčki in lončki	predmet
> 600	zadeva	predmet
> 601	zadovoljen	čustvo
> 602	zaključek	značilnost
> 603	zapis	vsebina
> 604	zaplenjeni blag	predmet
> 605	zasenčene luči	značilnost
> 606	zaspanje	značilnost
> 607	začetek pomladi	značilnost
> 608	začetna postaja	prostor
> 609	zdravje	značilnost
> 610	zdravnik	oseba
> 611	zdravstvena knjižica	dokument
> 612	zeleni poganjki	predmet
> 613	zemlja	predmet
> 614	zgodba o mačku	dogodek
> 615	zimskega spanja	značilnost
> 616	zlato medaljo	predmet
> 617	zmagovalec	oseba
> 618	zmaji	mitološka bitja
> 619	znameniti medved	značilnost
> 620	znamenje	zvočni signal
> 621	znanje	značilnost
> 622	značko	predmet
> 623	zob	predmet
> 624	zob	značilnost
> 625	zobobol	značilnost
> 626	zobozdravnik	oseba
> 627	zobozdravnik	prostor
> 628	zrak	element
> 629	zvezek	predmet
> 630	zvok	značilnost
> 631	zvončki	predmet
> 632	čakalnica	prostor
> 633	čarovniki	značilnost
> 634	čarovništvo mačka	značilnost
> 635	časopisi	predmet
> 636	čebulice	predmet
> 637	čelade, vrv, gasilske sekirice	predmet
> 638	četa	skupina
> 639	četrta brzina	značilnost
> 640	čiste petke	značilnost
> 641	član padalskega društva	članstvo
> 642	črni kmet	predmet
> 643	črni kralj	figurka
> 644	črni lev	žival
> 645	čudež	značilnost
> 646	čudo	značilnost
> 647	šah	igra
> 648	šahist	značilnost
> 649	šahovnica	predmet
> 650	šahovski velemojster	značilnost
> 651	šivilja	poklic
> 652	škarje	orodje
> 653	škatlice	predmet
> 654	škodo	značilnost
> 655	šofer	poklic
> 656	šofer medvedjega avtobusa	značilnost
> 657	šoferske umetnine	značilnost
> 658	šok	značilnost
> 659	šola	prostor
> 660	šolarji	oseba
> 661	šolo	prostor
> 662	športni dan	dogodek
> 663	štadilnik	predmet
> 664	šteje	značilnost
> 665	štiri tigra	žival
> 666	štiripasovnica	predmet
> 667	Žužu	oseba
> 668	Žužu številka 1	značilnost
> 669	Žužu številka 2	oseba
> 670	Žužuja	prostor
> 671	žabje skoke	vaja
> 672	železnica	predmet
> 673	žirafe	žival
> 674	živalski vrt	prostor
> 675	živčen	značilnost
> 676	žongler	značilnost
> 677	žonglerska točka	dogodek
> 678	žvižganje	značilnost
> 679	žvrgolij	značilnost

```sql
SELECT CHUNK_ID, head.ID as HEAD_ID,  tail.ID as TAIL_ID, s.relation, s.text
FROM GRAPH_RELATIONS_STG S
INNER JOIN  GRAPH_ENTITIES_STORY head ON head.ENTITY_NAME=s.head and head.ENTITY_TYPE = s.head_type
INNER JOIN  GRAPH_ENTITIES_STORY tail ON tail.ENTITY_NAME=s.tail and tail.ENTITY_TYPE = s.tail_type;
```

> CHUNK_ID	HEAD_ID	TAIL_ID	RELATION	TEXT
> 31	244	430	ima lastnost	oseba: medvedja mamica -[ima lastnost]-> značilnost: rada
> 31	244	264	se pogovarja	oseba: medvedja mamica -[se pogovarja]-> predmet: medvedki
> 31	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 31	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki
> 31	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 31	535	48	odgovarja	oseba: učitelj -[odgovarja]-> oseba: Piki
> 31	48	244	trdi	oseba: Piki -[trdi]-> oseba: medvedja mamica
> 32	244	288	dela	oseba: medvedja mamica -[dela]-> oseba: možakar
> 32	288	264	prezema	oseba: možakar -[prezema]-> predmet: medvedki
> 32	264	525	prevozi	predmet: medvedki -[prevozi]-> prostor: trgovina
> 32	525	264	dela	prostor: trgovina -[dela]-> predmet: medvedki
> 32	264	216	ima lastnost	predmet: medvedki -[ima lastnost]-> značilnost: listek
> 32	48	166	se nahaja	oseba: Piki -[se nahaja]-> prostor: izložba
> 32	48	333	vzpostavi stik	oseba: Piki -[vzpostavi stik]-> oseba: očeta
> 32	333	48	kupi	oseba: očeta -[kupi]-> oseba: Piki
> 33	535	48	poboža	oseba: učitelj -[poboža]-> oseba: Piki
> 33	535	244	sanja	oseba: učitelj -[sanja]-> oseba: medvedja mamica
> 33	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki
> 33	535	361	piše	oseba: učitelj -[piše]-> dokument: pismo
> 33	535	89	pošilja	oseba: učitelj -[pošilja]-> oseba: babi
> 33	535	113	pošilja	oseba: učitelj -[pošilja]-> oseba: ded
> 33	535	48	pošilja	oseba: učitelj -[pošilja]-> oseba: Piki
> 33	48	535	vpraša	oseba: Piki -[vpraša]-> oseba: učitelj
> 34	48	23	stanuje	oseba: Piki -[stanuje]-> prostor: Ljubljana
> 34	48	669	piše	oseba: Piki -[piše]-> oseba: Žužu številka 2
> 34	48	535	živi z	oseba: Piki -[živi z]-> oseba: učitelj
> 34	48	669	se spominja	oseba: Piki -[se spominja]-> oseba: Žužu številka 2
> 34	48	668	ima vzdevek	oseba: Piki -[ima vzdevek]-> značilnost: Žužu številka 1
> 35	50	23	živi	oseba: Piki Jakob -[živi]-> prostor: Ljubljana
> 35	50	246	hodi v šolo	oseba: Piki Jakob -[hodi v šolo]-> prostor: medvedja šola
> 35	50	259	ima prijatelje	oseba: Piki Jakob -[ima prijatelje]-> oseba: medvedji prijatelji
> 35	50	305	piše	oseba: Piki Jakob -[piše]-> oseba: neznani prejemnik
> 35	50	393	pošlje pismo	oseba: Piki Jakob -[pošlje pismo]-> prostor: pošta
> 35	50	535	ima učitelja	oseba: Piki Jakob -[ima učitelja]-> oseba: učitelj
> 36	48	72	piše	oseba: Piki -[piše]-> oseba: Tedi
> 36	48	33	piše	oseba: Piki -[piše]-> oseba: Marmeladov
> 36	48	4	piše	oseba: Piki -[piše]-> oseba: Berenson
> 36	48	35	piše	oseba: Piki -[piše]-> oseba: Medolizis
> 36	48	39	piše	oseba: Piki -[piše]-> oseba: Mečkovič
> 36	48	667	prejme pismo	oseba: Piki -[prejme pismo]-> oseba: Žužu
> 36	667	267	vozi	oseba: Žužu -[vozi]-> predmet: metro
> 36	242	233	jedajo	oseba: medvedi v Parizu -[jedajo]-> značilnost: med
> 36	242	659	hodijo	oseba: medvedi v Parizu -[hodijo]-> prostor: šola
> 36	242	267	vozijo	oseba: medvedi v Parizu -[vozijo]-> predmet: metro
> 37	535	23	poisal	oseba: učitelj -[poisal]-> prostor: Ljubljana
> 37	23	278	je blizu	prostor: Ljubljana -[je blizu]-> prostor: morje
> 37	667	50	pošlje pismo	oseba: Žužu -[pošlje pismo]-> oseba: Piki Jakob
> 37	394	50	išče	oseba: poštar -[išče]-> oseba: Piki Jakob
> 37	50	99	stanuje	oseba: Piki Jakob -[stanuje]-> prostor: blok
> 37	394	499	pozvonil	oseba: poštar -[pozvonil]-> prostor: stopnišče
> 38	50	394	prejme pismo	oseba: Piki Jakob -[prejme pismo]-> oseba: poštar
> 38	50	535	stanuje	oseba: Piki Jakob -[stanuje]-> oseba: učitelj
> 38	50	395	ima poštno skrinjico	oseba: Piki Jakob -[ima poštno skrinjico]-> predmet: poštna skrinjica
> 38	394	50	išče	oseba: poštar -[išče]-> oseba: Piki Jakob
> 38	535	50	ima podnajemnika	oseba: učitelj -[ima podnajemnika]-> oseba: Piki Jakob
> 39	48	128	je član	oseba: Piki -[je član]-> skupina: družina
> 39	48	625	ima zobobol	oseba: Piki -[ima zobobol]-> značilnost: zobobol
> 39	48	626	obiskuje	oseba: Piki -[obiskuje]-> oseba: zobozdravnik
> 39	535	625	ima zobobol	oseba: učitelj -[ima zobobol]-> značilnost: zobobol
> 39	150	625	ima zobobol	oseba: govorec -[ima zobobol]-> značilnost: zobobol
> 39	48	312	prejema zdravstvo	oseba: Piki -[prejema zdravstvo]-> predmet: obkladke
> 40	48	545	ima težavo	oseba: Piki -[ima težavo]-> značilnost: uši
> 40	48	449	obvezan z	oseba: Piki -[obvezan z]-> predmet: ruto
> 40	48	626	obiskuje	oseba: Piki -[obiskuje]-> oseba: zobozdravnik
> 40	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki
> 40	626	48	je prijatelj	oseba: zobozdravnik -[je prijatelj]-> oseba: Piki
> 40	48	535	se strinja	oseba: Piki -[se strinja]-> oseba: učitelj
> 40	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki
> 41	48	535	se strinja	oseba: Piki -[se strinja]-> oseba: učitelj
> 41	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki
> 41	48	626	potrpi	oseba: Piki -[potrpi]-> oseba: zobozdravnik
> 41	48	449	je obvezan	oseba: Piki -[je obvezan]-> predmet: ruto
> 41	535	332	vpraša	oseba: učitelj -[vpraša]-> oseba: otrok
> 41	235	624	more biti bolan	oseba: medved -[more biti bolan]-> značilnost: zob
> 42	48	498	sedel	oseba: Piki -[sedel]-> predmet: stol
> 42	48	611	ima zdravstveno knjižico	oseba: Piki -[ima zdravstveno knjižico]-> dokument: zdravstvena knjižica
> 42	102	611	pobira	oseba: bolniška sestra -[pobira]-> dokument: zdravstvena knjižica
> 42	48	102	se sreča	oseba: Piki -[se sreča]-> oseba: bolniška sestra
> 42	48	632	čaka	oseba: Piki -[čaka]-> prostor: čakalnica
> 42	102	50	kliče	oseba: bolniška sestra -[kliče]-> oseba: Piki Jakob
> 42	50	610	obiskuje	oseba: Piki Jakob -[obiskuje]-> oseba: zdravnik
> 42	610	50	pozdravlja	oseba: zdravnik -[pozdravlja]-> oseba: Piki Jakob
> 42	50	625	ima težavo	oseba: Piki Jakob -[ima težavo]-> značilnost: zobobol
> 43	610	48	zdravi	oseba: zdravnik -[zdravi]-> oseba: Piki
> 43	48	498	sedel	oseba: Piki -[sedel]-> predmet: stol
> 43	610	48	preiskuje	oseba: zdravnik -[preiskuje]-> oseba: Piki
> 43	610	192	uporablja	oseba: zdravnik -[uporablja]-> predmet: kovinska paličica
> 43	48	610	odgovarja	oseba: Piki -[odgovarja]-> oseba: zdravnik
> 43	48	624	ima bolečino	oseba: Piki -[ima bolečino]-> značilnost: zob
> 44	610	48	preiskuje	oseba: zdravnik -[preiskuje]-> oseba: Piki
> 44	610	424	uporablja	oseba: zdravnik -[uporablja]-> predmet: prst
> 44	48	624	čuti bolečino	oseba: Piki -[čuti bolečino]-> značilnost: zob
> 44	48	610	grize	oseba: Piki -[grize]-> oseba: zdravnik
> 44	610	48	ukazuje	oseba: zdravnik -[ukazuje]-> oseba: Piki
> 44	48	610	se izogiba	oseba: Piki -[se izogiba]-> oseba: zdravnik
> 45	48	623	ima zob	oseba: Piki -[ima zob]-> predmet: zob
> 45	535	623	ima zob	oseba: učitelj -[ima zob]-> predmet: zob
> 45	535	626	obiskuje	oseba: učitelj -[obiskuje]-> oseba: zobozdravnik
> 45	626	535	plombira	oseba: zobozdravnik -[plombira]-> oseba: učitelj
> 45	626	48	pregleda	oseba: zobozdravnik -[pregleda]-> oseba: Piki
> 45	48	627	odhaja	oseba: Piki -[odhaja]-> prostor: zobozdravnik
> 46	48	626	ugrizne	oseba: Piki -[ugrizne]-> oseba: zobozdravnik
> 46	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 46	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj
> 46	535	414	opozarja	oseba: učitelj -[opozarja]-> oseba: pripovedovalec
> 46	246	662	organizira	prostor: medvedja šola -[organizira]-> dogodek: športni dan
> 46	535	572	pripravlja	oseba: učitelj -[pripravlja]-> aktivnost: vožnja z žičnico
> 47	225	174	sestavi	oseba: matador -[sestavi]-> predmet: kabino
> 47	173	590	drsela	predmet: kabina -[drsela]-> predmet: vrvi
> 47	535	484	naznani	oseba: učitelj -[naznani]-> dogodek: spomladanski kros
> 47	73	529	šeži	oseba: Timika -[šeži]-> predmet: uho
> 47	18	158	razpara	oseba: Josip Jupiter -[razpara]-> predmet: hlačnico
> 48	48	73	govori	oseba: Piki -[govori]-> oseba: Timika
> 48	73	48	odgovarja	oseba: Timika -[odgovarja]-> oseba: Piki
> 48	535	418	pripravlja	oseba: učitelj -[pripravlja]-> prostor: proga
> 48	251	418	tekajo	oseba: medvedji -[tekajo]-> prostor: proga
> 48	617	616	prejme	oseba: zmagovalec -[prejme]-> predmet: zlato medaljo
> 48	617	553	prejme	oseba: zmagovalec -[prejme]-> predmet: veliko hruško
> 49	251	98	tekajo	oseba: medvedji -[tekajo]-> prostor: berezov gaj
> 49	251	120	tekajo	oseba: medvedji -[tekajo]-> prostor: dnevna soba
> 49	251	125	podrli	oseba: medvedji -[podrli]-> predmet: drevesa
> 49	535	125	postavi	oseba: učitelj -[postavi]-> predmet: drevesa
> 49	132	215	izgubi	predmet: fikus -[izgubi]-> predmet: lista
> 49	251	429	tekajo	oseba: medvedji -[tekajo]-> prostor: pusto planjavo
> 49	251	159	tekajo	oseba: medvedji -[tekajo]-> prostor: hodnik
> 49	251	284	imajo težave	oseba: medvedji -[imajo težave]-> prostor: močvirni predeli
> 49	251	191	imajo težave	oseba: medvedji -[imajo težave]-> prostor: kopalnica
> 49	12	444	pade	oseba: Filip -[pade]-> prostor: ribnik
> 49	12	93	pade	oseba: Filip -[pade]-> predmet: banjo
> 50	251	172	tekajo	oseba: medvedji -[tekajo]-> prostor: južno gričevje
> 50	251	480	tekajo	oseba: medvedji -[tekajo]-> prostor: spalnica
> 50	251	593	srečajo	oseba: medvedji -[srečajo]-> značilnost: vzpon
> 50	251	492	srečajo	oseba: medvedji -[srečajo]-> prostor: stari grad
> 50	251	329	srečajo	oseba: medvedji -[srečajo]-> predmet: omara
> 50	48	576	prileze	oseba: Piki -[prileze]-> prostor: vrh
> 50	48	151	teče	oseba: Piki -[teče]-> prostor: greben
> 50	48	510	teče	oseba: Piki -[teče]-> prostor: temna goščava
> 50	48	435	teče	oseba: Piki -[teče]-> predmet: razmetane učiteljeve igrače
> 50	48	266	skoke	oseba: Piki -[skoke]-> prostor: mehki travnik
> 50	48	383	skoke	oseba: Piki -[skoke]-> predmet: postelja
> 51	48	266	drvi	oseba: Piki -[drvi]-> prostor: mehki travnik
> 51	48	266	okleni	oseba: Piki -[okleni]-> prostor: mehki travnik
> 51	48	162	spozna	oseba: Piki -[spozna]-> žival: hudi tiger
> 51	48	226	spozna	oseba: Piki -[spozna]-> žival: maček
> 51	263	162	vrže	oseba: medvedji športniki -[vrže]-> žival: hudi tiger
> 51	162	48	zajaha	žival: hudi tiger -[zajaha]-> oseba: Piki
> 52	162	48	drvi	žival: hudi tiger -[drvi]-> oseba: Piki
> 52	162	318	išče	žival: hudi tiger -[išče]-> predmet: odprto okno
> 52	535	327	zapre	oseba: učitelj -[zapre]-> predmet: okna
> 52	162	206	teče	žival: hudi tiger -[teče]-> prostor: kuhinja
> 52	162	535	zavre	žival: hudi tiger -[zavre]-> oseba: učitelj
> 52	48	106	prileti	oseba: Piki -[prileti]-> prostor: cilj
> 53	48	616	prejme	oseba: Piki -[prejme]-> predmet: zlato medaljo
> 53	48	552	prejme	oseba: Piki -[prejme]-> predmet: velikansko hruško
> 53	507	48	zaploskajo	oseba: tekmovalci -[zaploskajo]-> oseba: Piki
> 53	535	60	potrdi	oseba: učitelj -[potrdi]-> dogodek: Pikijeva zmaga
> 53	48	513	jezdi	oseba: Piki -[jezdi]-> žival: tiger
> 53	48	160	razdeli	oseba: Piki -[razdeli]-> predmet: hruško
> 53	513	198	bruši	žival: tiger -[bruši]-> predmet: kremplje
> 54	48	582	ima	oseba: Piki -[ima]-> zdravstvena stanja: vročino
> 54	247	454	so	oseba: medvedje -[so]-> značilnost: sami doma
> 54	535	67	odpelje	oseba: učitelj -[odpelje]-> prostor: Sora
> 54	48	595	sedel	oseba: Piki -[sedel]-> prostor: zaboj za igrače
> 54	48	326	premišljeva	oseba: Piki -[premišljeva]-> značilnost: ohladitev
> 54	48	70	zagleda	oseba: Piki -[zagleda]-> oseba: Stari Marko
> 54	48	70	pogovarja	oseba: Piki -[pogovarja]-> oseba: Stari Marko
> 55	70	48	zamomlja	oseba: Stari Marko -[zamomlja]-> oseba: Piki
> 55	48	70	zajavka	oseba: Piki -[zajavka]-> oseba: Stari Marko
> 55	70	479	predlaga	oseba: Stari Marko -[predlaga]-> zdravstvena stanja: sončarica
> 55	70	188	predlaga	oseba: Stari Marko -[predlaga]-> zdravstvena stanja: kolera
> 55	48	70	vzklika	oseba: Piki -[vzklika]-> oseba: Stari Marko
> 55	48	70	razjezi	oseba: Piki -[razjezi]-> oseba: Stari Marko
> 55	70	48	svetuje	oseba: Stari Marko -[svetuje]-> oseba: Piki
> 56	48	384	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: poten
> 56	48	663	uporablja	oseba: Piki -[uporablja]-> predmet: štadilnik
> 56	48	218	uporablja	oseba: Piki -[uporablja]-> predmet: lonček za čaj
> 56	48	367	uporablja	oseba: Piki -[uporablja]-> predmet: pokrovko
> 56	48	502	uporablja	oseba: Piki -[uporablja]-> predmet: tableto
> 56	48	497	dostopa	oseba: Piki -[dostopa]-> prostor: stenska lekarnica
> 56	497	653	vsebuje	prostor: stenska lekarnica -[vsebuje]-> predmet: škatlice
> 57	48	70	pokliče	oseba: Piki -[pokliče]-> oseba: Stari Marko
> 57	48	70	vpraša	oseba: Piki -[vpraša]-> oseba: Stari Marko
> 57	70	81	svetuje	oseba: Stari Marko -[svetuje]-> zdravilo: aspirin
> 57	48	306	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: neznanje
> 57	70	621	ima lastnost	oseba: Stari Marko -[ima lastnost]-> značilnost: znanje
> 57	81	580	zdravi	zdravilo: aspirin -[zdravi]-> bolezen: vročina
> 58	48	81	zaužije	oseba: Piki -[zaužije]-> zdravilo: aspirin
> 58	48	579	pije	oseba: Piki -[pije]-> napitek: vroči lipov čaj
> 58	48	580	ima lastnost	oseba: Piki -[ima lastnost]-> bolezen: vročina
> 58	48	470	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: slabost
> 58	48	535	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: učitelj
> 58	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki
> 59	48	580	ima lastnost	oseba: Piki -[ima lastnost]-> bolezen: vročina
> 59	535	516	uporablja	oseba: učitelj -[uporablja]-> orodje: toplomer
> 59	535	48	meri	oseba: učitelj -[meri]-> oseba: Piki
> 59	48	509	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: telesna temperatura
> 59	48	535	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: učitelj
> 59	535	48	pojasnjuje	oseba: učitelj -[pojasnjuje]-> oseba: Piki
> 59	111	581	ima lastnost	čas: dan -[ima lastnost]-> značilnost: vročina
> 60	535	48	pojasnjuje	oseba: učitelj -[pojasnjuje]-> oseba: Piki
> 60	48	580	ima lastnost	oseba: Piki -[ima lastnost]-> bolezen: vročina
> 60	535	48	pomaga	oseba: učitelj -[pomaga]-> oseba: Piki
> 60	48	190	se ohladi	oseba: Piki -[se ohladi]-> predmet: kopalna kada
> 60	48	357	se greje	oseba: Piki -[se greje]-> predmet: peč
> 61	48	640	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: čiste petke
> 61	48	619	je primer	oseba: Piki -[je primer]-> značilnost: znameniti medved
> 61	535	392	se pripravlja	oseba: učitelj -[se pripravlja]-> dogodek: počitnice
> 61	535	48	vzame	oseba: učitelj -[vzame]-> oseba: Piki
> 61	48	122	ima izkušnjo	oseba: Piki -[ima izkušnjo]-> čustvo: dolgčas
> 61	48	407	je bil	oseba: Piki -[je bil]-> značilnost: predšolski medvedek
> 62	48	256	dobi	oseba: Piki -[dobi]-> predmet: medvedji kovček
> 62	48	245	spravlja	oseba: Piki -[spravlja]-> predmet: medvedja prtljaso
> 62	48	392	gre na	oseba: Piki -[gre na]-> dogodek: počitnice
> 62	535	150	prepriča	oseba: učitelj -[prepriča]-> oseba: govorec
> 62	150	535	se strinja	oseba: govorec -[se strinja]-> oseba: učitelj
> 62	252	392	gre na	skupina: medvedji -[gre na]-> dogodek: počitnice
> 63	535	150	zahteva	oseba: učitelj -[zahteva]-> oseba: govorec
> 63	535	226	prosi	oseba: učitelj -[prosi]-> žival: maček
> 63	150	535	se upira	oseba: govorec -[se upira]-> oseba: učitelj
> 63	535	150	vpraša	oseba: učitelj -[vpraša]-> oseba: govorec
> 63	150	614	se spominja	oseba: govorec -[se spominja]-> dogodek: zgodba o mačku
> 63	150	226	odloča	oseba: govorec -[odloča]-> žival: maček
> 64	48	193	polni	oseba: Piki -[polni]-> predmet: kovček
> 64	48	349	vzame	oseba: Piki -[vzame]-> predmet: perilo
> 64	48	455	vzame	oseba: Piki -[vzame]-> obutev: sandale
> 64	48	362	vzame	oseba: Piki -[vzame]-> pripomoček: plavalni obroč
> 64	48	170	vzame	oseba: Piki -[vzame]-> plovilo: jadrnica
> 64	48	279	obleče	oseba: Piki -[obleče]-> oblačila: mornarska majica
> 64	535	48	opazuje	oseba: učitelj -[opazuje]-> oseba: Piki
> 64	150	535	dodaja	oseba: govorec -[dodaja]-> oseba: učitelj
> 65	535	150	svetuje	oseba: učitelj -[svetuje]-> oseba: govorec
> 65	150	535	se strinja	oseba: govorec -[se strinja]-> oseba: učitelj
> 65	150	105	skriva	oseba: govorec -[skriva]-> predmet: cigarete
> 65	535	83	vozi	oseba: učitelj -[vozi]-> vozilo: avto
> 65	48	486	sedel	oseba: Piki -[sedel]-> prostor: sprednji sedež
> 65	48	569	pozdravlja	oseba: Piki -[pozdravlja]-> skupina: vozniki
> 65	48	370	prejema	oseba: Piki -[prejema]-> gesta: poljubček
> 65	469	278	pripelje	skupina: skupina -[pripelje]-> prostor: morje
> 66	48	601	je	oseba: Piki -[je]-> čustvo: zadovoljen
> 66	48	443	lovi	oseba: Piki -[lovi]-> žival: ribe
> 66	48	478	se veseli	oseba: Piki -[se veseli]-> pojav: sonce
> 66	48	472	se veseli	oseba: Piki -[se veseli]-> pojav: slana voda
> 66	48	471	se veseli	oseba: Piki -[se veseli]-> hrana: sladoled
> 66	48	433	piše	oseba: Piki -[piše]-> dokument: razglednica
> 66	48	433	podpiše	oseba: Piki -[podpiše]-> dokument: razglednica
> 66	48	570	obiskuje	oseba: Piki -[obiskuje]-> učilnica: vozniška šola
> 66	48	657	opazuje	oseba: Piki -[opazuje]-> značilnost: šoferske umetnine
> 67	48	511	vpisal v tečaj	oseba: Piki -[vpisal v tečaj]-> predmet: tečaj
> 67	48	420	uči	oseba: Piki -[uči]-> značilnost: prometne znake
> 67	48	150	ima učitelja	oseba: Piki -[ima učitelja]-> oseba: govorec
> 67	150	48	postal učitelj	oseba: govorec -[postal učitelj]-> oseba: Piki
> 67	48	656	želi postati	oseba: Piki -[želi postati]-> značilnost: šofer medvedjega avtobusa
> 68	48	629	risal	oseba: Piki -[risal]-> predmet: zvezek
> 68	48	629	sanja	oseba: Piki -[sanja]-> predmet: zvezek
> 68	48	425	opravil tečaj	oseba: Piki -[opravil tečaj]-> predmet: prva pomoč
> 68	48	88	vozi	oseba: Piki -[vozi]-> predmet: avtomobilček
> 68	48	88	ima mnenje	oseba: Piki -[ima mnenje]-> predmet: avtomobilček
> 68	48	535	sodeluje z	oseba: Piki -[sodeluje z]-> oseba: učitelj
> 69	535	48	razložil	oseba: učitelj -[razložil]-> oseba: Piki
> 69	535	150	postavil	oseba: učitelj -[postavil]-> oseba: govorec
> 69	48	432	skomignil	oseba: Piki -[skomignil]-> značilnost: rameni
> 69	48	86	peljala	oseba: Piki -[peljala]-> prostor: avtodrom
> 69	48	481	naučil	oseba: Piki -[naučil]-> značilnost: speljevanja in ustavljanja
> 69	48	411	menjal	oseba: Piki -[menjal]-> značilnost: prestave
> 69	48	364	dodajal in odvzemal	oseba: Piki -[dodajal in odvzemal]-> značilnost: plin
> 70	48	419	vozi	oseba: Piki -[vozi]-> prostor: prometne ulice
> 70	48	666	prevozi	oseba: Piki -[prevozi]-> predmet: štiripasovnica
> 70	48	605	prižgal	oseba: Piki -[prižgal]-> značilnost: zasenčene luči
> 70	48	519	sreča	oseba: Piki -[sreča]-> predmet: tovornjak
> 70	48	519	pobliskal	oseba: Piki -[pobliskal]-> predmet: tovornjak
> 70	48	519	se razjezi	oseba: Piki -[se razjezi]-> predmet: tovornjak
> 71	48	121	prižgal	oseba: Piki -[prižgal]-> značilnost: dolge luči
> 71	150	48	prepričal	oseba: govorec -[prepričal]-> oseba: Piki
> 71	48	519	približuje se	oseba: Piki -[približuje se]-> predmet: tovornjak
> 71	48	519	ugotovil	oseba: Piki -[ugotovil]-> predmet: tovornjak
> 71	150	48	ugovarjal	oseba: govorec -[ugovarjal]-> oseba: Piki
> 71	48	519	zagledal se	oseba: Piki -[zagledal se]-> predmet: tovornjak
> 72	48	522	ponovil	oseba: Piki -[ponovil]-> značilnost: trditev
> 72	48	441	razkril	oseba: Piki -[razkril]-> značilnost: resnica
> 72	150	48	vprašal	oseba: govorec -[vprašal]-> oseba: Piki
> 72	48	226	odkril	oseba: Piki -[odkril]-> žival: maček
> 72	48	181	zatrobil	oseba: Piki -[zatrobil]-> značilnost: klik
> 72	226	658	poskočil	žival: maček -[poskočil]-> značilnost: šok
> 72	226	639	ucvrl	žival: maček -[ucvrl]-> značilnost: četrta brzina
> 73	48	168	priglasil	oseba: Piki -[priglasil]-> predmet: izpit
> 73	535	169	predsedoval	oseba: učitelj -[predsedoval]-> organizacija: izpitna komisija
> 73	48	82	vozil	oseba: Piki -[vozil]-> predmet: avto
> 73	48	82	parkiral	oseba: Piki -[parkiral]-> predmet: avto
> 73	48	594	pozabil	oseba: Piki -[pozabil]-> predmet: vzvratno ogledalo
> 73	48	445	izvajal	oseba: Piki -[izvajal]-> značilnost: ritenska vožnja
> 73	535	178	seštel	oseba: učitelj -[seštel]-> značilnost: kazenske točke
> 74	48	520	nabral	oseba: Piki -[nabral]-> značilnost: točke
> 74	48	168	opravil	oseba: Piki -[opravil]-> predmet: izpit
> 74	48	571	dobil	oseba: Piki -[dobil]-> dokument: vozniško dovoljenje
> 74	48	281	upravlja	oseba: Piki -[upravlja]-> predmet: moterne vozilo
> 74	48	496	pogostil	oseba: Piki -[pogostil]-> predmet: steklenica ribezovega soka
> 74	48	84	vozi	oseba: Piki -[vozi]-> predmet: avtobus
> 74	48	568	delal	oseba: Piki -[delal]-> poklic: voznik avtobusa
> 75	48	18	izbral	oseba: Piki -[izbral]-> oseba: Josip Jupiter
> 75	18	489	bil	oseba: Josip Jupiter -[bil]-> poklic: sprevodnik
> 75	48	253	vozil	oseba: Piki -[vozil]-> predmet: medvedji avtobus
> 75	18	567	prodajal	oseba: Josip Jupiter -[prodajal]-> predmet: vozni listki
> 75	48	372	ugotovil	oseba: Piki -[ugotovil]-> značilnost: pomanjkanje
> 75	18	372	ugotovil	oseba: Josip Jupiter -[ugotovil]-> značilnost: pomanjkanje
> 76	18	48	rekel	oseba: Josip Jupiter -[rekel]-> oseba: Piki
> 76	48	18	odgovoril	oseba: Piki -[odgovoril]-> oseba: Josip Jupiter
> 76	48	381	predlagal	oseba: Piki -[predlagal]-> značilnost: postajališča
> 76	84	381	ustavil	predmet: avtobus -[ustavil]-> značilnost: postajališča
> 76	386	608	vstopali	oseba: potniki -[vstopali]-> prostor: začetna postaja
> 76	386	189	izstopali	oseba: potniki -[izstopali]-> prostor: končna postaja
> 77	48	373	tožil	oseba: Piki -[tožil]-> značilnost: pomanjkanje potnikov
> 77	18	48	rekel	oseba: Josip Jupiter -[rekel]-> oseba: Piki
> 77	660	27	vstopili	oseba: šolarji -[vstopili]-> prostor: MEDVEDJI DOM
> 77	660	26	izstopili	oseba: šolarji -[izstopili]-> prostor: MEDVEDJA ŠOLA
> 77	48	66	ustavil	oseba: Piki -[ustavil]-> prostor: STARI GOJZAR
> 77	18	2	rekel	oseba: Josip Jupiter -[rekel]-> oseba: Benjamin
> 77	2	18	odgovoril	oseba: Benjamin -[odgovoril]-> oseba: Josip Jupiter
> 78	18	2	govori	oseba: Josip Jupiter -[govori]-> oseba: Benjamin
> 78	2	18	govori	oseba: Benjamin -[govori]-> oseba: Josip Jupiter
> 78	18	2	dejstvo	oseba: Josip Jupiter -[dejstvo]-> oseba: Benjamin
> 78	37	85	dejstvo	oseba: Medvedje -[dejstvo]-> prostor: avtobus
> 78	69	32	dejstvo	oseba: Sprevodnik -[dejstvo]-> oseba: Marko Prvi
> 78	69	31	dejstvo	oseba: Sprevodnik -[dejstvo]-> oseba: Marko Drugi
> 78	18	68	delo	oseba: Josip Jupiter -[delo]-> delo: Sprevodnik
> 78	2	85	potovanje	oseba: Benjamin -[potovanje]-> prostor: avtobus
> 78	32	85	potovanje	oseba: Marko Prvi -[potovanje]-> prostor: avtobus
> 78	31	85	potovanje	oseba: Marko Drugi -[potovanje]-> prostor: avtobus
> 79	32	175	vrže	oseba: Marko Prvi -[vrže]-> predmet: kamen
> 79	48	85	vozi	oseba: Piki -[vozi]-> prostor: avtobus
> 79	69	32	mahajo	oseba: Sprevodnik -[mahajo]-> oseba: Marko Prvi
> 79	69	386	govori	oseba: Sprevodnik -[govori]-> oseba: potniki
> 79	12	69	govori	oseba: Filip -[govori]-> oseba: Sprevodnik
> 79	18	487	predstavi	oseba: Josip Jupiter -[predstavi]-> delo: sprevodnik
> 79	32	48	pobrana	oseba: Marko Prvi -[pobrana]-> oseba: Piki
> 80	12	18	govori	oseba: Filip -[govori]-> oseba: Josip Jupiter
> 80	12	18	počil	oseba: Filip -[počil]-> oseba: Josip Jupiter
> 80	18	12	pretepa	oseba: Josip Jupiter -[pretepa]-> oseba: Filip
> 80	48	85	vozi	oseba: Piki -[vozi]-> prostor: avtobus
> 80	48	85	zavrl	oseba: Piki -[zavrl]-> prostor: avtobus
> 80	85	229	trči	prostor: avtobus -[trči]-> predmet: mačji rep
> 80	228	85	prevrnil	oseba: mačji lastnik -[prevrnil]-> prostor: avtobus
> 80	48	229	vidi	oseba: Piki -[vidi]-> predmet: mačji rep
> 81	247	85	pobirajo	oseba: medvedje -[pobirajo]-> prostor: avtobus
> 81	488	247	se prikaže	oseba: sprevodnik -[se prikaže]-> oseba: medvedje
> 81	48	518	pomaga	oseba: Piki -[pomaga]-> oseba: tovariš
> 81	48	101	se pognal	oseba: Piki -[se pognal]-> dogodek: bojni metež
> 81	247	517	tolče	oseba: medvedje -[tolče]-> predmet: torbice
> 81	247	116	tolče	oseba: medvedje -[tolče]-> predmet: dežniki
> 81	560	412	prekinja	oseba: višji policijski inšpektor -[prekinja]-> dogodek: pretep
> 81	560	413	odpelje	oseba: višji policijski inšpektor -[odpelje]-> oseba: pretepači
> 81	560	413	izpraša	oseba: višji policijski inšpektor -[izpraša]-> oseba: pretepači
> 81	560	199	naloži kazni	oseba: višji policijski inšpektor -[naloži kazni]-> oseba: krivci
> 82	69	261	odide	oseba: Sprevodnik -[odide]-> prostor: medvedji zapor
> 82	48	566	preneha	oseba: Piki -[preneha]-> dejavnost: voziti avtobusa
> 82	37	654	vrnejo	oseba: Medvedje -[vrnejo]-> značilnost: škodo
> 82	24	423	zbirajo	oseba: Ljudje -[zbirajo]-> značilnost: prostovoljne prispevke
> 82	48	150	obiskuje	oseba: Piki -[obiskuje]-> oseba: govorec
> 82	69	150	obiskuje	oseba: Sprevodnik -[obiskuje]-> oseba: govorec
> 82	16	48	daje	oseba: Govorec -[daje]-> oseba: Piki
> 82	16	69	daje	oseba: Govorec -[daje]-> oseba: Sprevodnik
> 82	48	150	obljublja	oseba: Piki -[obljublja]-> oseba: govorec
> 82	69	150	obljublja	oseba: Sprevodnik -[obljublja]-> oseba: govorec
> 82	76	309	odpre	oseba: Učitelj -[odpre]-> dogodek: novoletni sejem
> 135	76	434	zahteval	oseba: Učitelj -[zahteval]-> značilnost: razlago
> 135	48	607	ponudil	oseba: Piki -[ponudil]-> značilnost: začetek pomladi
> 135	48	402	pojasnil	oseba: Piki -[pojasnil]-> značilnost: prebujanje gozdnih medvedov
> 135	48	79	ponudil	oseba: Piki -[ponudil]-> značilnost: Velika Medvednica
> 135	76	403	sprejel	oseba: Učitelj -[sprejel]-> značilnost: predlog
> 135	76	485	sestavljal	oseba: Učitelj -[sestavljal]-> značilnost: spored
> 135	76	355	določil	oseba: Učitelj -[določil]-> značilnost: pevce, igralce, plesalce in recitatorje
> 136	48	563	postal	oseba: Piki -[postal]-> značilnost: vodja moškega pevskega zbora
> 136	286	352	vadi	skupina: moški pevskega zbora -[vadi]-> značilnost: pesem o dvanajstih razbojnikih
> 136	7	343	trkal	oseba: Dirigent -[trkal]-> predmet: paličico
> 136	7	204	vpil	oseba: Dirigent -[vpil]-> značilnost: krulba
> 136	78	374	prišla	dogodek: Velika Medvednica -[prišla]-> značilnost: pomlad
> 137	75	661	okrasili	skupina: Učenci -[okrasili]-> prostor: šolo
> 137	75	551	zasedli	skupina: Učenci -[zasedli]-> prostor: velika šolska dvorana
> 137	48	319	stal	oseba: Piki -[stal]-> prostor: odru
> 137	48	234	zatrobil	oseba: Piki -[zatrobil]-> predmet: medeninast rog
> 137	257	319	hiteli	skupina: medvedji pevskega zbora -[hiteli]-> prostor: odru
> 137	257	457	pretegovali	skupina: medvedji pevskega zbora -[pretegovali]-> značilnost: se
> 137	257	615	zbudili	skupina: medvedji pevskega zbora -[zbudili]-> značilnost: zimskega spanja
> 138	260	351	zložil	oseba: medvedji učitelj -[zložil]-> značilnost: pesem
> 138	48	354	izuril	oseba: Piki -[izuril]-> skupina: pevce
> 138	356	353	peli	skupina: pevci -[peli]-> značilnost: pesmijo
> 138	315	356	ploskalo	skupina: občinstvo -[ploskalo]-> skupina: pevci
> 138	315	466	ploskalo	skupina: občinstvo -[ploskalo]-> oseba: skladatelj
> 138	74	363	nastopil	skupina: Trio Marko -[nastopil]-> značilnost: ples
> 139	241	505	igrali	skupina: medvedi -[igrali]-> predmet: tamburice
> 139	29	316	plesali	skupina: Marki -[plesali]-> prostor: oder
> 139	143	378	zahtevali	skupina: gledalci -[zahtevali]-> značilnost: ponovitev
> 139	73	63	nastopila	oseba: Timika -[nastopila]-> značilnost: Pomlad
> 139	2	236	nastopil	oseba: Benjamin -[nastopil]-> značilnost: medved Domberdan
> 140	63	9	zaklicala	značilnost: Pomlad -[zaklicala]-> značilnost: Domberdan
> 140	9	63	odgovarjal	značilnost: Domberdan -[odgovarjal]-> značilnost: Pomlad
> 140	63	564	zlila	značilnost: Pomlad -[zlila]-> predmet: vodo
> 140	274	417	smehali	skupina: mladi gledalci -[smehali]-> značilnost: prizor
> 140	439	417	nastopili	skupina: recitatorji -[nastopili]-> značilnost: prizor
> 140	258	602	nastopil	skupina: medvedji pevski zbor -[nastopil]-> značilnost: zaključek
> 141	258	308	zapel	skupina: medvedji pevski zbor -[zapel]-> značilnost: nove pesmi
> 141	308	20	vsebujejo	značilnost: nove pesmi -[vsebujejo]-> značilnost: Ko medved zjutraj v šolo gre
> 141	308	34	vsebujejo	značilnost: nove pesmi -[vsebujejo]-> značilnost: Medene lonce ližemo
> 141	308	38	vsebujejo	značilnost: nove pesmi -[vsebujejo]-> značilnost: Medvedje hrabri smo gasilci
> 141	308	62	vsebujejo	značilnost: nove pesmi -[vsebujejo]-> značilnost: Pomald -medvedji letni čas
> 141	241	270	prejeli	skupina: medvedi -[prejeli]-> predmet: minihrenovko
> 141	241	220	prejeli	skupina: medvedi -[prejeli]-> predmet: makismed
> 141	540	473	pripravila	oseba: učiteljeva mama -[pripravila]-> značilnost: slavnostno kosilo
> 141	535	388	predlagal	oseba: učitelj -[predlagal]-> značilnost: potovanje v Pariz
> 142	535	46	ponovil	oseba: učitelj -[ponovil]-> prostor: Pariz
> 142	48	670	bi obiskal	oseba: Piki -[bi obiskal]-> prostor: Žužuja
> 142	535	387	predlagal	oseba: učitelj -[predlagal]-> značilnost: potovanje
> 142	535	464	predlagal	oseba: učitelj -[predlagal]-> značilnost: severni tečaj
> 142	150	535	vprašal	oseba: govorec -[vprašal]-> oseba: učitelj
> 142	150	535	rekel	oseba: govorec -[rekel]-> oseba: učitelj
> 142	150	535	vprašal	oseba: govorec -[vprašal]-> oseba: učitelj
> 142	535	87	odgovoril	oseba: učitelj -[odgovoril]-> predmet: avtom
> 143	535	463	predlagal	oseba: učitelj -[predlagal]-> prostor: severni tečaj
> 143	48	460	bi rad videl	oseba: Piki -[bi rad videl]-> žival: severne medvede
> 143	48	359	bi rad videl	oseba: Piki -[bi rad videl]-> žival: pingvine
> 143	48	290	bi rad videl	oseba: Piki -[bi rad videl]-> žival: mrože
> 143	535	87	predlagal	oseba: učitelj -[predlagal]-> predmet: avtom
> 143	535	11	predlagal	oseba: učitelj -[predlagal]-> etnična skupina: Eskimi
> 143	535	345	predlagal	oseba: učitelj -[predlagal]-> predmet: pasja vprega
> 144	48	461	ima željo	oseba: Piki -[ima željo]-> žival: severni medvedi
> 144	48	214	ima željo	oseba: Piki -[ima željo]-> žival: levi
> 144	48	514	ima željo	oseba: Piki -[ima željo]-> žival: tigri
> 144	48	474	ima željo	oseba: Piki -[ima željo]-> žival: sloni
> 144	48	80	ima željo	oseba: Piki -[ima željo]-> žival: antilope
> 144	48	673	ima željo	oseba: Piki -[ima željo]-> žival: žirafe
> 144	48	203	ima željo	oseba: Piki -[ima željo]-> žival: krokodili
> 144	48	618	ima željo	oseba: Piki -[ima željo]-> mitološka bitja: zmaji
> 144	535	48	se pogovarja	oseba: učitelj -[se pogovarja]-> oseba: Piki
> 144	618	398	se pojavljajo	mitološka bitja: zmaji -[se pojavljajo]-> literarna vrsta: pravljica
> 145	535	398	govori	oseba: učitelj -[govori]-> literarna vrsta: pravljica
> 145	535	150	se pogovarja	oseba: učitelj -[se pogovarja]-> oseba: govorec
> 145	150	398	govori	oseba: govorec -[govori]-> literarna vrsta: pravljica
> 145	150	358	predlaga	oseba: govorec -[predlaga]-> način potovanja: peš
> 145	535	45	želi	oseba: učitelj -[želi]-> mesto: Pariz
> 145	48	45	želi	oseba: Piki -[želi]-> mesto: Pariz
> 145	150	45	trdi	oseba: govorec -[trdi]-> mesto: Pariz
> 145	150	462	trdi	oseba: govorec -[trdi]-> geografska lokacija: severni tečaj
> 145	150	1	trdi	oseba: govorec -[trdi]-> kontinent: Afrika
> 146	150	442	misli	oseba: govorec -[misli]-> značilnost: resno
> 146	535	150	govori	oseba: učitelj -[govori]-> oseba: govorec
> 146	535	150	prosi	oseba: učitelj -[prosi]-> oseba: govorec
> 146	150	674	predlaga	oseba: govorec -[predlaga]-> prostor: živalski vrt
> 146	150	535	obljubljajo	oseba: govorec -[obljubljajo]-> oseba: učitelj
> 146	150	535	vozi	oseba: govorec -[vozi]-> oseba: učitelj
> 146	535	493	pripravlja	oseba: učitelj -[pripravlja]-> predmet: stari kruh
> 147	535	150	govori	oseba: učitelj -[govori]-> oseba: govorec
> 147	535	48	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Piki
> 147	150	535	pogovarja se	oseba: govorec -[pogovarja se]-> oseba: učitelj
> 147	535	674	potrdi	oseba: učitelj -[potrdi]-> prostor: živalski vrt
> 147	150	535	obljubljajo	oseba: govorec -[obljubljajo]-> oseba: učitelj
> 147	150	674	obiskuje	oseba: govorec -[obiskuje]-> prostor: živalski vrt
> 147	150	462	potuje	oseba: govorec -[potuje]-> geografska lokacija: severni tečaj
> 147	150	65	obiskuje	oseba: govorec -[obiskuje]-> prostor: Rožnik
> 147	150	330	opazuje	oseba: govorec -[opazuje]-> žival: opice
> 147	150	456	vozi	oseba: govorec -[vozi]-> predmet: sane
> 148	633	534	so	značilnost: čarovniki -[so]-> značilnost: učenci
> 148	534	182	so	značilnost: učenci -[so]-> značilnost: kljukci
> 148	182	269	so	značilnost: kljukci -[so]-> značilnost: mile jere
> 148	269	431	so	značilnost: mile jere -[so]-> značilnost: radovedneži
> 148	431	379	so	značilnost: radovedneži -[so]-> značilnost: poredneži
> 109	52	598	znosita	skupina: Piki in učitelj -[znosita]-> predmet: zabojčke, lončke, prst in vrečke s čebulicami
> 109	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki
> 109	48	636	sadita	oseba: Piki -[sadita]-> predmet: čebulice
> 109	48	222	pričakuje	oseba: Piki -[pričakuje]-> značilnost: mamina veselje
> 109	535	222	upajo	oseba: učitelj -[upajo]-> značilnost: mamina veselje
> 109	52	453	delata	skupina: Piki in učitelj -[delata]-> aktivnost: saditev čebulic
> 109	52	613	zalijeta	skupina: Piki in učitelj -[zalijeta]-> predmet: zemlja
> 109	52	635	pospravita	skupina: Piki in učitelj -[pospravita]-> predmet: časopisi
> 109	52	422	pometeta	skupina: Piki in učitelj -[pometeta]-> prostor: prostor
> 110	52	183	sedeta	skupina: Piki in učitelj -[sedeta]-> predmet: klop
> 110	535	391	vzklikne	oseba: učitelj -[vzklikne]-> značilnost: pozabljen napis
> 110	48	541	odzove	oseba: Piki -[odzove]-> značilnost: učiteljeva skrb
> 110	535	223	pojasnjuje	oseba: učitelj -[pojasnjuje]-> značilnost: mamina vprašanje
> 110	48	295	predlaga	oseba: Piki -[predlaga]-> značilnost: napis
> 110	48	636	spomina	oseba: Piki -[spomina]-> predmet: čebulice
> 111	48	165	predlaga	oseba: Piki -[predlaga]-> dejanje: izkopavanje
> 111	48	535	pomirja	oseba: Piki -[pomirja]-> oseba: učitelj
> 111	221	599	opazi	oseba: mama -[opazi]-> predmet: zabojčki in lončki
> 111	599	503	vsebujejo	predmet: zabojčki in lončki -[vsebujejo]-> predmet: tablice
> 111	503	546	so postavljene	predmet: tablice -[so postavljene]-> prostor: v prst
> 112	221	535	govori	oseba: mama -[govori]-> oseba: učitelj
> 112	535	477	priznava	oseba: učitelj -[priznava]-> dejanje: sodelovanje z Pikijem
> 112	48	535	sodeluje	oseba: Piki -[sodeluje]-> oseba: učitelj
> 112	535	221	govori	oseba: učitelj -[govori]-> oseba: mama
> 112	536	446	posadita	oseba: učitelj in Piki -[posadita]-> predmet: rože
> 113	585	291	drži se	oseba: vrtnarja -[drži se]-> značilnost: mulasto
> 113	119	375	tekajo	čas: dnevi -[tekajo]-> čas: pomlad
> 113	599	612	vsebujejo	predmet: zabojčki in lončki -[vsebujejo]-> predmet: zeleni poganjki
> 113	631	596	rasli	predmet: zvončki -[rasli]-> prostor: zabojček z napisom: rumeni tulipan
> 114	535	307	zatrjuje	oseba: učitelj -[zatrjuje]-> značilnost: ni potrebno obvestiti
> 114	585	397	zatrjujeta	oseba: vrtnarja -[zatrjujeta]-> značilnost: pravilnost tablic
> 114	535	226	omenja	oseba: učitelj -[omenja]-> žival: maček
> 114	631	438	se spreminjajo	predmet: zvončki -[se spreminjajo]-> predmet: rdeči tulipani
> 114	447	275	se spreminjajo	predmet: rožnate hijacinte -[se spreminjajo]-> predmet: modre hijacinte
> 114	448	96	se spreminjajo	predmet: rumeni krokusi -[se spreminjajo]-> predmet: beli krokusi
> 115	150	535	govori	oseba: govorec -[govori]-> oseba: učitelj
> 115	535	634	namiguje	oseba: učitelj -[namiguje]-> značilnost: čarovništvo mačka
> 115	150	227	čaka	oseba: govorec -[čaka]-> predmet: maček na metli
> 115	535	107	vabi	oseba: učitelj -[vabi]-> prostor: cirkus
> 115	107	300	poteka	prostor: cirkus -[poteka]-> čas: nedelja popoldne
> 116	108	311	vabi	prostor: cirkus bežigrad -[vabi]-> oseba: obiskovalci
> 116	108	591	nastopajo	prostor: cirkus bežigrad -[nastopajo]-> predmet: vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba
> 116	150	535	opozarja	oseba: govorec -[opozarja]-> oseba: učitelj
> 116	535	144	ogrožen	oseba: učitelj -[ogrožen]-> predmet: gnila jajca in paradižnike
> 116	117	144	ogrožen	oseba: direktor -[ogrožen]-> predmet: gnila jajca in paradižnike
> 117	535	150	pomirja	oseba: učitelj -[pomirja]-> oseba: govorec
> 117	535	185	potrjuje	oseba: učitelj -[potrjuje]-> predmet: klovni
> 117	535	514	potrjuje	oseba: učitelj -[potrjuje]-> žival: tigri
> 117	535	150	imenuje	oseba: učitelj -[imenuje]-> oseba: govorec
> 117	150	90	žonglira	oseba: govorec -[žonglira]-> predmet: balinčki
> 117	117	676	potrjuje	oseba: direktor -[potrjuje]-> značilnost: žongler
> 117	117	201	daje	oseba: direktor -[daje]-> predmet: krogle
> 118	150	548	svetuje	oseba: govorec -[svetuje]-> dejanje: vajanje
> 118	314	674	ogleda	oseba: občinstvo -[ogleda]-> prostor: živalski vrt
> 118	250	421	ima	žival: medvedje -[ima]-> značilnost: prosti vstop
> 118	217	129	plačajo	oseba: ljudje -[plačajo]-> predmet: en dinar
> 118	674	180	vsebuje	prostor: živalski vrt -[vsebuje]-> predmet: kletka z zelenima papagajema
> 118	514	328	so razporejeni	žival: tigri -[so razporejeni]-> prostor: okrog kletke
> 118	293	226	je podoben	žival: največji tiger -[je podoben]-> žival: maček
> 119	644	179	opazuje	žival: črni lev -[opazuje]-> prostor: kletka
> 119	644	504	stegne	žival: črni lev -[stegne]-> dejanje: taco
> 119	644	524	čuti	žival: črni lev -[čuti]-> značilnost: trdoto papagajevega kljuna
> 119	150	440	stopi	oseba: govorec -[stopi]-> predmet: rep črnega leva
> 119	644	674	zbeža	žival: črni lev -[zbeža]-> prostor: živalski vrt
> 119	117	513	ujema	oseba: direktor -[ujema]-> žival: tiger
> 119	314	406	odhaja	oseba: občinstvo -[odhaja]-> dogodek: predstava
> 120	117	100	igra	oseba: direktor -[igra]-> predmet: blokflavta
> 120	117	21	izvaja	oseba: direktor -[izvaja]-> glasba: Koračnica palčkov
> 120	117	592	nastopa	oseba: direktor -[nastopa]-> vloga: vrvohodec
> 120	184	314	zabavajo	oseba: klovni -[zabavajo]-> oseba: občinstvo
> 120	6	71	sodeluje	oseba: Debeli Bongo -[sodeluje]-> oseba: Suhi Grintež
> 120	28	8	sodeluje	oseba: Mali Makec -[sodeluje]-> oseba: Dolgi Jakec
> 120	41	22	sodeluje	oseba: Nemi Lukec -[sodeluje]-> oseba: Lapasti Kljukec
> 120	25	677	izvaja	oseba: Lovikrogla -[izvaja]-> dogodek: žonglerska točka
> 121	150	677	se namuči	oseba: govorec -[se namuči]-> dogodek: žonglerska točka
> 121	150	200	izgubi	oseba: govorec -[izgubi]-> predmet: krogla
> 121	117	124	pove	oseba: direktor -[pove]-> dogodek: dresura tigrov
> 121	213	674	pobegnejo	žival: lev in tigri -[pobegnejo]-> prostor: živalski vrt
> 121	409	665	zaleže	žival: preostali tiger -[zaleže]-> žival: štiri tigra
> 122	48	117	sodeluje	oseba: Piki -[sodeluje]-> oseba: direktor
> 122	48	513	upravlja	oseba: Piki -[upravlja]-> žival: tiger
> 122	117	513	upravlja	oseba: direktor -[upravlja]-> žival: tiger
> 122	513	313	skok	žival: tiger -[skok]-> predmet: obroč
> 122	513	200	prinaša	žival: tiger -[prinaša]-> predmet: krogla
> 123	55	337	postane	oseba: Piki padalec -[postane]-> poklic: padalec
> 123	143	530	zaploskajo	skupina: gledalci -[zaploskajo]-> oseba: umetnik
> 123	145	40	igra	skupina: godba -[igra]-> pesem: Na planincah luštno biti
> 123	143	47	poje	skupina: gledalci -[poje]-> pesem: Pastirica žgance kuha, notri pade ena muha
> 124	48	641	postane	oseba: Piki -[postane]-> članstvo: član padalskega društva
> 124	48	133	gleda	oseba: Piki -[gleda]-> film: film o padalcih
> 124	48	97	ima vtis	oseba: Piki -[ima vtis]-> predmet: beli mehurčki
> 125	48	341	ustanovi	oseba: Piki -[ustanovi]-> organizacija: padalsko društvo
> 125	48	18	sodeluje	oseba: Piki -[sodeluje]-> oseba: Josip Jupiter
> 125	48	70	sodeluje	oseba: Piki -[sodeluje]-> oseba: Stari Marko
> 125	48	12	sodeluje	oseba: Piki -[sodeluje]-> oseba: Filip
> 125	221	334	izdeluje	oseba: mama -[izdeluje]-> predmet: padala
> 125	535	339	postane	oseba: učitelj -[postane]-> poklic: padalski polkovnik
> 125	535	547	sestavi	oseba: učitelj -[sestavi]-> dokument: vadbeni urnik
> 126	415	671	vadi	skupina: pripravniki -[vadi]-> vaja: žabje skoke
> 126	415	368	vadi	skupina: pripravniki -[vadi]-> vaja: polet
> 126	415	340	uporablja	skupina: pripravniki -[uporablja]-> oprema: padalski telovniki
> 126	415	589	vadi	skupina: pripravniki -[vadi]-> vaja: vrtoglavica
> 126	371	415	prevrže	oseba: polkovnik -[prevrže]-> skupina: pripravniki
> 126	371	414	povabi	oseba: polkovnik -[povabi]-> oseba: pripovedovalec
> 127	30	321	čaka	oseba: Marko -[čaka]-> prostor: odskočišče
> 127	371	30	daje znak	oseba: polkovnik -[daje znak]-> oseba: Marko
> 127	70	320	izvaja	oseba: Stari Marko -[izvaja]-> dejanje: odskok
> 127	338	628	ujema	predmet: padalo -[ujema]-> element: zrak
> 127	556	336	vpliva	element: veter -[vpliva]-> oseba: padalec
> 127	336	91	pade	oseba: padalec -[pade]-> prostor: balkon
> 127	390	336	opozarja	oseba: poveljnik -[opozarja]-> oseba: padalec
> 128	371	18	opozarja	oseba: polkovnik -[opozarja]-> oseba: Josip Jupiter
> 128	18	320	izvaja	oseba: Josip Jupiter -[izvaja]-> dejanje: odskok
> 128	18	70	sreča	oseba: Josip Jupiter -[sreča]-> oseba: Stari Marko
> 128	556	18	vpliva	element: veter -[vpliva]-> oseba: Josip Jupiter
> 128	371	532	hotel	oseba: polkovnik -[hotel]-> dogodek: ustaviti tekmovanje
> 128	48	371	prosi	oseba: Piki -[prosi]-> oseba: polkovnik
> 129	48	321	skoči	oseba: Piki -[skoči]-> prostor: odskočišče
> 129	48	521	pristane	oseba: Piki -[pristane]-> prostor: trava za blokom
> 129	12	321	skoči	oseba: Filip -[skoči]-> prostor: odskočišče
> 129	12	152	obvisi	oseba: Filip -[obvisi]-> predmet: grm forsicije
> 129	535	414	vpraša	oseba: učitelj -[vpraša]-> oseba: pripovedovalec
> 129	414	131	oceni	oseba: pripovedovalec -[oceni]-> skupina: fantje
> 130	535	414	govori	oseba: učitelj -[govori]-> oseba: pripovedovalec
> 130	535	92	pomigne	oseba: učitelj -[pomigne]-> prostor: balkoni
> 130	535	414	prosi	oseba: učitelj -[prosi]-> oseba: pripovedovalec
> 130	414	535	se strinja	oseba: pripovedovalec -[se strinja]-> oseba: učitelj
> 130	414	127	obiskuje	oseba: pripovedovalec -[obiskuje]-> prostor: drugo nadstropje
> 130	490	414	odpre	oseba: stara gospa -[odpre]-> oseba: pripovedovalec
> 131	414	147	pride	oseba: pripovedovalec -[pride]-> oseba: gospa
> 131	147	414	ponovi	oseba: gospa -[ponovi]-> oseba: pripovedovalec
> 131	414	147	pojasnjuje	oseba: pripovedovalec -[pojasnjuje]-> oseba: gospa
> 131	147	414	izrazi skeptično	oseba: gospa -[izrazi skeptično]-> oseba: pripovedovalec
> 131	414	147	pojasnjuje	oseba: pripovedovalec -[pojasnjuje]-> oseba: gospa
> 131	147	414	misli	oseba: gospa -[misli]-> oseba: pripovedovalec
> 132	147	70	najde	oseba: gospa -[najde]-> oseba: Stari Marko
> 132	147	414	se smeji	oseba: gospa -[se smeji]-> oseba: pripovedovalec
> 132	414	147	se zahvali	oseba: pripovedovalec -[se zahvali]-> oseba: gospa
> 132	115	414	odpre	oseba: deček -[odpre]-> oseba: pripovedovalec
> 132	115	342	se ukvarja	oseba: deček -[se ukvarja]-> šport: padalstvom
> 132	414	48	pobere	oseba: pripovedovalec -[pobere]-> oseba: Piki
> 132	414	12	pobere	oseba: pripovedovalec -[pobere]-> oseba: Filip
> 132	287	123	se vrne	skupina: moštvo -[se vrne]-> prostor: domov
> 132	371	508	napove	oseba: polkovnik -[napove]-> dogodek: tekmovali
> 133	61	335	odlikoval	oseba: Polkovnik -[odlikoval]-> oseba: padalci
> 133	335	42	prejeli	oseba: padalci -[prejeli]-> nagrada: POGUMNI PADALEC
> 133	61	622	hotel	oseba: Polkovnik -[hotel]-> predmet: značko
> 134	61	44	pojasnil	oseba: Polkovnik -[pojasnil]-> značilnost: PP
> 134	48	403	prispeval	oseba: Piki -[prispeval]-> značilnost: predlog
> 134	76	404	zbiral	oseba: Učitelj -[zbiral]-> značilnost: predloge
> 134	76	118	tehtal	oseba: Učitelj -[tehtal]-> značilnost: dneve
> 134	36	400	ni imela	prostor: Medvedja šola -[ni imela]-> značilnost: praznika
> 1	50	99	stanuje	oseba: Piki Jakob -[stanuje]-> prostor: blok
> 1	50	246	hodi v	oseba: Piki Jakob -[hodi v]-> prostor: medvedja šola
> 1	50	130	ima učitelja	oseba: Piki Jakob -[ima učitelja]-> oseba: fantek
> 2	48	539	ima očeta	oseba: Piki -[ima očeta]-> oseba: učiteljev oče
> 2	48	539	se razumeva	oseba: Piki -[se razumeva]-> oseba: učiteljev oče
> 2	535	539	ima očeta	oseba: učitelj -[ima očeta]-> oseba: učiteljev oče
> 2	535	539	ima težave	oseba: učitelj -[ima težave]-> oseba: učiteljev oče
> 2	48	246	hodi v	oseba: Piki -[hodi v]-> prostor: medvedja šola
> 2	48	243	vozi	oseba: Piki -[vozi]-> predmet: medvedja kočija
> 3	30	235	je	oseba: Marko -[je]-> oseba: medved
> 3	12	235	je	oseba: Filip -[je]-> oseba: medved
> 3	73	235	je	oseba: Timika -[je]-> oseba: medved
> 3	18	235	je	oseba: Josip Jupiter -[je]-> oseba: medved
> 3	2	235	je	oseba: Benjamin -[je]-> oseba: medved
> 3	14	350	je	oseba: Floki -[je]-> žival: pes
> 3	14	246	hodi v	oseba: Floki -[hodi v]-> prostor: medvedja šola
> 3	48	211	je	oseba: Piki -[je]-> značilnost: leteči medved
> 3	535	14	spiva z	oseba: učitelj -[spiva z]-> oseba: Floki
> 4	48	155	prileti	oseba: Piki -[prileti]-> predmet: helikopter
> 4	48	539	poščegeta	oseba: Piki -[poščegeta]-> oseba: učiteljev oče
> 4	48	238	ima vzdevek	oseba: Piki -[ima vzdevek]-> značilnost: medvedbudilka
> 4	48	535	gre spat z	oseba: Piki -[gre spat z]-> oseba: učitelj
> 4	48	535	pripoveduje	oseba: Piki -[pripoveduje]-> oseba: učitelj
> 4	48	539	poboža	oseba: Piki -[poboža]-> oseba: učiteljev oče
> 4	48	535	poboža	oseba: Piki -[poboža]-> oseba: učitelj
> 4	48	167	je izobražen	oseba: Piki -[je izobražen]-> značilnost: izobražen
> 5	48	135	pogovarja se	oseba: Piki -[pogovarja se]-> jezik: francosko
> 5	48	46	bil je	oseba: Piki -[bil je]-> prostor: Pariz
> 5	48	49	ima ime	oseba: Piki -[ima ime]-> značilnost: Piki
> 5	48	255	uči	oseba: Piki -[uči]-> jezik: medvedji jezik
> 5	48	659	se uči	oseba: Piki -[se uči]-> prostor: šola
> 5	535	540	ima mamo	oseba: učitelj -[ima mamo]-> oseba: učiteljeva mama
> 5	535	164	je nezaupljiv	oseba: učitelj -[je nezaupljiv]-> značilnost: imenitne jedi
> 6	205	221	opazuje	oseba: kuhelmuc -[opazuje]-> oseba: mama
> 6	221	207	reže	oseba: mama -[reže]-> značilnost: kumarice
> 6	221	146	dodaja	oseba: mama -[dodaja]-> značilnost: gorčica
> 6	221	219	dodaja	oseba: mama -[dodaja]-> značilnost: majonezo
> 6	221	134	pripravlja	oseba: mama -[pripravlja]-> jedi: francoska solata
> 6	535	646	strmi v	oseba: učitelj -[strmi v]-> značilnost: čudo
> 6	535	221	odgovarja	oseba: učitelj -[odgovarja]-> oseba: mama
> 7	221	535	prosi	oseba: mama -[prosi]-> oseba: učitelj
> 7	535	221	odgovarja	oseba: učitelj -[odgovarja]-> oseba: mama
> 7	535	298	ima mnenje	oseba: učitelj -[ima mnenje]-> značilnost: ne maram čudnih jedi
> 7	221	535	vztraja	oseba: mama -[vztraja]-> oseba: učitelj
> 7	535	297	ima mnenje	oseba: učitelj -[ima mnenje]-> značilnost: ne bom jedel
> 7	221	535	ubeda	oseba: mama -[ubeda]-> oseba: učitelj
> 7	535	171	trdi	oseba: učitelj -[trdi]-> značilnost: jed je strup
> 8	221	161	postane	oseba: mama -[postane]-> značilnost: hud
> 8	221	535	vpraša	oseba: mama -[vpraša]-> oseba: učitelj
> 8	535	221	odgovarja	oseba: učitelj -[odgovarja]-> oseba: mama
> 8	221	535	grozi	oseba: mama -[grozi]-> oseba: učitelj
> 8	221	48	vzame	oseba: mama -[vzame]-> oseba: Piki
> 8	221	48	vpraša	oseba: mama -[vpraša]-> oseba: Piki
> 8	48	221	odgovarja	oseba: Piki -[odgovarja]-> oseba: mama
> 8	221	535	primerja	oseba: mama -[primerja]-> oseba: učitelj
> 9	221	535	govori	oseba: mama -[govori]-> oseba: učitelj
> 9	535	221	molči	oseba: učitelj -[molči]-> oseba: mama
> 9	221	48	nudi	oseba: mama -[nudi]-> oseba: Piki
> 9	535	54	trdi	oseba: učitelj -[trdi]-> značilnost: Piki ne mara francoske solate
> 9	48	365	je	oseba: Piki -[je]-> značilnost: plišasti medvedek
> 9	48	645	je	oseba: Piki -[je]-> značilnost: čudež
> 9	48	134	poliže	oseba: Piki -[poliže]-> jedi: francoska solata
> 9	221	48	vpraša	oseba: mama -[vpraša]-> oseba: Piki
> 9	48	221	odgovarja	oseba: Piki -[odgovarja]-> oseba: mama
> 10	48	134	pojede	oseba: Piki -[pojede]-> jedi: francoska solata
> 10	48	458	oblizne se	oseba: Piki -[oblizne se]-> oseba: sebe
> 10	48	221	priklonil se	oseba: Piki -[priklonil se]-> oseba: mama
> 10	221	535	vpraša	oseba: mama -[vpraša]-> oseba: učitelj
> 10	535	221	odgovarja	oseba: učitelj -[odgovarja]-> oseba: mama
> 10	535	53	trdi	oseba: učitelj -[trdi]-> značilnost: Piki je Francoz
> 10	535	48	primerja	oseba: učitelj -[primerja]-> oseba: Piki
> 10	535	221	pove	oseba: učitelj -[pove]-> oseba: mama
> 11	221	543	ne ve	oseba: mama -[ne ve]-> značilnost: učiteljevo mnenje
> 11	535	501	ostane pri	oseba: učitelj -[ostane pri]-> značilnost: svojem mnenju
> 11	48	369	sedel	oseba: Piki -[sedel]-> prostor: polica
> 11	48	609	je zdrav	oseba: Piki -[je zdrav]-> značilnost: zdravje
> 11	262	531	vsebuje	prostor: medvedji šola -[vsebuje]-> dogodek: ura
> 11	535	240	uči	oseba: učitelj -[uči]-> oseba: medvedi
> 11	535	240	ponavlja	oseba: učitelj -[ponavlja]-> oseba: medvedi
> 11	535	240	vpraša	oseba: učitelj -[vpraša]-> oseba: medvedi
> 12	12	535	odgovarja	oseba: Filip -[odgovarja]-> oseba: učitelj
> 12	535	12	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Filip
> 12	73	535	odgovarja	oseba: Timika -[odgovarja]-> oseba: učitelj
> 12	535	73	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Timika
> 12	50	535	odgovarja	oseba: Piki Jakob -[odgovarja]-> oseba: učitelj
> 12	535	50	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Piki Jakob
> 12	50	231	govori o	oseba: Piki Jakob -[govori o]-> žival: mačke
> 12	231	268	izdajajo zvok	žival: mačke -[izdajajo zvok]-> značilnost: mijavkanje
> 12	231	678	izdajajo zvok	žival: mačke -[izdajajo zvok]-> značilnost: žvižganje
> 12	428	149	izdajajo zvok	žival: ptički -[izdajajo zvok]-> značilnost: gostolij
> 12	428	679	izdajajo zvok	žival: ptički -[izdajajo zvok]-> značilnost: žvrgolij
> 12	428	678	izdajajo zvok	žival: ptički -[izdajajo zvok]-> značilnost: žvižganje
> 12	350	209	izdajajo zvok	žival: pes -[izdajajo zvok]-> značilnost: lajanje
> 13	535	48	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Piki
> 13	48	535	pogovarja se	oseba: Piki -[pogovarja se]-> oseba: učitelj
> 13	48	226	opazuje	oseba: Piki -[opazuje]-> žival: maček
> 13	226	678	izdaja zvok	žival: maček -[izdaja zvok]-> značilnost: žvižganje
> 13	535	659	opozarja	oseba: učitelj -[opozarja]-> prostor: šola
> 13	231	268	izdaja zvok	žival: mačke -[izdaja zvok]-> značilnost: mijavkanje
> 13	48	678	slišal	oseba: Piki -[slišal]-> značilnost: žvižganje
> 13	48	294	delal	oseba: Piki -[delal]-> predmet: naloga
> 14	48	226	vidi	oseba: Piki -[vidi]-> žival: maček
> 14	535	48	odgovarja	oseba: učitelj -[odgovarja]-> oseba: Piki
> 14	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj
> 14	226	678	izdaja zvok	žival: maček -[izdaja zvok]-> značilnost: žvižganje
> 14	535	232	trdi	oseba: učitelj -[trdi]-> značilnost: mačke ne žvižgajo
> 14	48	544	sprejema	oseba: Piki -[sprejema]-> značilnost: učiteljevo trditev
> 15	535	30	govori	oseba: učitelj -[govori]-> oseba: Marko
> 15	535	495	preneha	oseba: učitelj -[preneha]-> predmet: stavka
> 15	535	558	odhaja	oseba: učitelj -[odhaja]-> prostor: veža
> 15	535	285	sreča	oseba: učitelj -[sreča]-> oseba: moški
> 15	285	535	vpraša	oseba: moški -[vpraša]-> oseba: učitelj
> 15	535	285	odgovarja	oseba: učitelj -[odgovarja]-> oseba: moški
> 16	535	285	govori	oseba: učitelj -[govori]-> oseba: moški
> 16	285	535	govori	oseba: moški -[govori]-> oseba: učitelj
> 16	535	230	ima	oseba: učitelj -[ima]-> žival: mačka
> 16	285	535	vpraša	oseba: moški -[vpraša]-> oseba: učitelj
> 16	535	285	odgovarja	oseba: učitelj -[odgovarja]-> oseba: moški
> 16	285	535	pove	oseba: moški -[pove]-> oseba: učitelj
> 16	230	427	ubija	žival: mačka -[ubija]-> žival: ptičke
> 16	230	176	požre	žival: mačka -[požre]-> žival: kanarček
> 17	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 17	535	573	zapre	oseba: učitelj -[zapre]-> predmet: vrata
> 17	535	436	se vrne	oseba: učitelj -[se vrne]-> prostor: razred
> 17	535	248	govori	oseba: učitelj -[govori]-> osebe: medvedje
> 17	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 17	535	48	obstane	oseba: učitelj -[obstane]-> oseba: Piki
> 17	535	48	pove	oseba: učitelj -[pove]-> oseba: Piki
> 17	231	268	mijavkajo	žival: mačke -[mijavkajo]-> značilnost: mijavkanje
> 17	231	678	žvižgajo	žival: mačke -[žvižgajo]-> značilnost: žvižganje
> 18	48	600	pokima	oseba: Piki -[pokima]-> predmet: zadeva
> 18	48	647	igra	oseba: Piki -[igra]-> igra: šah
> 18	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 18	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj
> 18	535	48	obeta	oseba: učitelj -[obeta]-> oseba: Piki
> 18	48	650	sanja	oseba: Piki -[sanja]-> značilnost: šahovski velemojster
> 19	535	647	igra	oseba: učitelj -[igra]-> igra: šah
> 19	48	647	igra	oseba: Piki -[igra]-> igra: šah
> 19	535	186	napravi potezo	oseba: učitelj -[napravi potezo]-> predmet: kmet
> 19	48	186	napravi potezo	oseba: Piki -[napravi potezo]-> predmet: kmet
> 19	535	48	opozori	oseba: učitelj -[opozori]-> oseba: Piki
> 19	535	48	zmaguje	oseba: učitelj -[zmaguje]-> oseba: Piki
> 19	535	186	vzame	oseba: učitelj -[vzame]-> predmet: kmet
> 19	48	385	zamisli se	oseba: Piki -[zamisli se]-> predmet: poteza
> 20	535	675	postane	oseba: učitelj -[postane]-> značilnost: živčen
> 20	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 20	48	535	vpraša	oseba: Piki -[vpraša]-> oseba: učitelj
> 20	535	48	odgovarja	oseba: učitelj -[odgovarja]-> oseba: Piki
> 20	48	186	vzame	oseba: Piki -[vzame]-> predmet: kmet
> 20	48	642	postavi	oseba: Piki -[postavi]-> predmet: črni kmet
> 20	535	649	gleda	oseba: učitelj -[gleda]-> predmet: šahovnica
> 20	48	186	gleda	oseba: Piki -[gleda]-> predmet: kmet
> 20	48	186	požre	oseba: Piki -[požre]-> predmet: kmet
> 21	535	647	igra	oseba: učitelj -[igra]-> igra: šah
> 21	48	647	igra	oseba: Piki -[igra]-> igra: šah
> 21	48	542	jede	oseba: Piki -[jede]-> predmet: učiteljeve figure
> 21	535	197	ima	oseba: učitelj -[ima]-> predmet: kraljica
> 21	48	195	ima	oseba: Piki -[ima]-> predmet: kralj
> 21	535	48	ima prednost	oseba: učitelj -[ima prednost]-> oseba: Piki
> 22	535	647	napoveda	oseba: učitelj -[napoveda]-> igra: šah
> 22	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 22	57	114	beži	predmet: Pikijev kralj -[beži]-> predmet: deska
> 22	48	385	zamisli se	oseba: Piki -[zamisli se]-> predmet: poteza
> 22	535	48	opozori	oseba: učitelj -[opozori]-> oseba: Piki
> 22	535	48	zmaguje	oseba: učitelj -[zmaguje]-> oseba: Piki
> 22	48	385	odloči se	oseba: Piki -[odloči se]-> predmet: poteza
> 23	48	647	igra	oseba: Piki -[igra]-> igra: šah
> 23	535	647	igra	oseba: učitelj -[igra]-> igra: šah
> 23	48	401	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: prebrisan
> 23	535	196	dela potezo	oseba: učitelj -[dela potezo]-> figurka: kraljica
> 23	48	523	ima figurko	oseba: Piki -[ima figurko]-> figurka: trdnjava
> 23	535	643	opazi	oseba: učitelj -[opazi]-> figurka: črni kralj
> 23	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 23	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 24	48	648	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: šahist
> 24	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 24	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 24	48	500	požre	oseba: Piki -[požre]-> figurka: svoj kralj
> 24	535	48	obučuje	oseba: učitelj -[obučuje]-> oseba: Piki
> 24	48	647	igra	oseba: Piki -[igra]-> igra: šah
> 24	48	95	požre	oseba: Piki -[požre]-> figurka: bele figure
> 25	535	465	razume	oseba: učitelj -[razume]-> značilnost: situcija
> 25	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki
> 25	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 25	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki
> 25	48	95	požre	oseba: Piki -[požre]-> figurka: bele figure
> 25	535	465	izrazi zaskrbljenost	oseba: učitelj -[izrazi zaskrbljenost]-> značilnost: situcija
> 25	48	535	predlaga	oseba: Piki -[predlaga]-> oseba: učitelj
> 26	48	535	pripoveduje	oseba: Piki -[pripoveduje]-> oseba: učitelj
> 26	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki
> 26	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 26	48	244	ima izvor	oseba: Piki -[ima izvor]-> oseba: medvedja mamica
> 26	535	48	popravi	oseba: učitelj -[popravi]-> oseba: Piki
> 26	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj
> 27	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 27	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki
> 27	48	244	opisuje	oseba: Piki -[opisuje]-> oseba: medvedja mamica
> 27	244	651	deluje	oseba: medvedja mamica -[deluje]-> poklic: šivilja
> 27	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki
> 27	48	535	razlaga	oseba: Piki -[razlaga]-> oseba: učitelj
> 27	535	48	popravi	oseba: učitelj -[popravi]-> oseba: Piki
> 28	48	535	pripoveduje	oseba: Piki -[pripoveduje]-> oseba: učitelj
> 28	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki
> 28	48	664	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: šteje
> 28	244	202	ima orodje	oseba: medvedja mamica -[ima orodje]-> orodje: krojne pole
> 28	244	48	oblikuje	oseba: medvedja mamica -[oblikuje]-> oseba: Piki
> 28	48	450	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: rvav in bel pliš
> 28	48	212	primerja	oseba: Piki -[primerja]-> žival: lev
> 29	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki
> 29	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj
> 29	48	265	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: mehek
> 29	244	652	deluje	oseba: medvedja mamica -[deluje]-> orodje: škarje
> 29	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki
> 29	48	244	opazuje	oseba: Piki -[opazuje]-> oseba: medvedja mamica
> 29	244	550	ima material	oseba: medvedja mamica -[ima material]-> material: vata
> 29	244	280	ima material	oseba: medvedja mamica -[ima material]-> material: morska trava
> 30	244	652	deluje	oseba: medvedja mamica -[deluje]-> orodje: škarje
> 30	244	239	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedek
> 30	244	550	ima material	oseba: medvedja mamica -[ima material]-> material: vata
> 30	244	280	ima material	oseba: medvedja mamica -[ima material]-> material: morska trava
> 30	244	239	oblikuje	oseba: medvedja mamica -[oblikuje]-> predmet: medvedek
> 30	239	348	ima lastnost	predmet: medvedek -[ima lastnost]-> značilnost: pentlja
> 30	244	239	ogleda	oseba: medvedja mamica -[ogleda]-> predmet: medvedek
> 30	244	369	postavi	oseba: medvedja mamica -[postavi]-> prostor: polica
> 83	247	557	preživljajo	oseba: medvedje -[preživljajo]-> čas: večer
> 83	5	247	boksajo	oseba: Boksali -[boksajo]-> oseba: medvedje
> 83	14	383	pada	oseba: Floki -[pada]-> predmet: postelja
> 83	2	383	pada	oseba: Benjamin -[pada]-> predmet: postelja
> 83	76	112	je zaposlen	oseba: Učitelj -[je zaposlen]-> dogodek: dan otvoritve
> 83	247	148	se lišpajo	oseba: medvedje -[se lišpajo]-> dogodek: gostija
> 83	247	177	kupujejo	oseba: medvedje -[kupujejo]-> predmet: kariraste čepice
> 83	73	344	diši	oseba: Timika -[diši]-> značilnost: parfum
> 83	416	310	se začne	dogodek: prireditev -[se začne]-> čas: ob treh
> 83	422	120	je okrašen	prostor: prostor -[je okrašen]-> prostor: dnevna soba
> 83	422	459	je razdeljen	prostor: prostor -[je razdeljen]-> prostor: sejmišče in zabavišče
> 85	48	347	obiskuje	oseba: Piki -[obiskuje]-> prostor: paviljon z ogledali
> 85	19	347	obiskuje	oseba: Jupiter -[obiskuje]-> prostor: paviljon z ogledali
> 85	48	323	se smeji	oseba: Piki -[se smeji]-> predmet: ogledala
> 85	19	323	se smeji	oseba: Jupiter -[se smeji]-> predmet: ogledala
> 85	48	672	ogleduje	oseba: Piki -[ogleduje]-> predmet: železnica
> 85	19	672	ogleduje	oseba: Jupiter -[ogleduje]-> predmet: železnica
> 85	672	405	teče	predmet: železnica -[teče]-> prostor: predori
> 85	672	444	teče	predmet: železnica -[teče]-> prostor: ribnik
> 85	208	444	plava	predmet: ladjice -[plava]-> prostor: ribnik
> 85	672	346	se izgubi	predmet: železnica -[se izgubi]-> prostor: paviljon s skrivnostnim napisom
> 85	48	19	vpraša	oseba: Piki -[vpraša]-> oseba: Jupiter
> 85	48	157	gre	oseba: Piki -[gre]-> prostor: hiša strahov
> 86	19	48	govori	oseba: Jupiter -[govori]-> oseba: Piki
> 86	19	561	sedlo	oseba: Jupiter -[sedlo]-> predmet: vlakec
> 86	48	561	sedlo	oseba: Piki -[sedlo]-> predmet: vlakec
> 86	561	444	vozi	predmet: vlakec -[vozi]-> prostor: ribnik
> 86	561	289	zapelje	predmet: vlakec -[zapelje]-> prostor: mračen predor
> 86	561	153	stresel	predmet: vlakec -[stresel]-> značilnost: grmenje in bliskanje
> 86	561	10	zavozil	predmet: vlakec -[zavozil]-> prostor: Dvorana smrti
> 87	48	302	čuti	oseba: Piki -[čuti]-> predmet: nekaj
> 87	19	302	čuti	oseba: Jupiter -[čuti]-> predmet: nekaj
> 87	48	19	govori	oseba: Piki -[govori]-> oseba: Jupiter
> 87	19	48	govori	oseba: Jupiter -[govori]-> oseba: Piki
> 87	48	476	želi	oseba: Piki -[želi]-> predmet: smrt
> 87	48	19	govori	oseba: Piki -[govori]-> oseba: Jupiter
> 87	48	19	se smeji	oseba: Piki -[se smeji]-> oseba: Jupiter
> 87	19	48	se smeji	oseba: Jupiter -[se smeji]-> oseba: Piki
> 87	48	304	gre	oseba: Piki -[gre]-> prostor: nevarni predor
> 87	19	304	gre	oseba: Jupiter -[gre]-> prostor: nevarni predor
> 88	48	19	govori	oseba: Piki -[govori]-> oseba: Jupiter
> 88	19	48	govori	oseba: Jupiter -[govori]-> oseba: Piki
> 88	48	153	pelje	oseba: Piki -[pelje]-> značilnost: grmenje in bliskanje
> 88	19	153	pelje	oseba: Jupiter -[pelje]-> značilnost: grmenje in bliskanje
> 88	48	476	zgrabi	oseba: Piki -[zgrabi]-> predmet: smrt
> 88	19	476	zgrabi	oseba: Jupiter -[zgrabi]-> predmet: smrt
> 88	17	163	prisluži	prostor: Hiša strahov -[prisluži]-> značilnost: ime
> 88	476	51	zarjula	predmet: smrt -[zarjula]-> oseba: Piki in Jupiter
> 88	476	51	se iztrga	predmet: smrt -[se iztrga]-> oseba: Piki in Jupiter
> 88	476	156	pogine	predmet: smrt -[pogine]-> prostor: hiša
> 89	48	18	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: Josip Jupiter
> 89	48	535	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: učitelj
> 89	18	535	se pogovarja	oseba: Josip Jupiter -[se pogovarja]-> oseba: učitelj
> 89	48	296	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: navdušen
> 89	18	296	ima lastnost	oseba: Josip Jupiter -[ima lastnost]-> značilnost: navdušen
> 89	535	224	ima lastnost	oseba: učitelj -[ima lastnost]-> značilnost: manj navdušen
> 90	535	475	je jezen	oseba: učitelj -[je jezen]-> pojem: smrt
> 90	535	126	dela	oseba: učitelj -[dela]-> dejanje: drgniti parket
> 90	249	483	ima	skupina: medvedje -[ima]-> predmet: spominske knjige
> 90	535	2	vpraša	oseba: učitelj -[vpraša]-> oseba: Benjamin
> 90	2	535	odgovarja	oseba: Benjamin -[odgovarja]-> oseba: učitelj
> 90	535	271	zapisuje	oseba: učitelj -[zapisuje]-> dejanje: minus v vedenju
> 91	535	483	zadržal	oseba: učitelj -[zadržal]-> predmet: spominske knjige
> 91	535	604	listal	oseba: učitelj -[listal]-> predmet: zaplenjeni blag
> 91	535	15	preveril	oseba: učitelj -[preveril]-> predmet: Flokijeva knjiga
> 91	15	603	vsebuje	predmet: Flokijeva knjiga -[vsebuje]-> vsebina: zapis
> 91	603	237	opisuje	vsebina: zapis -[opisuje]-> oseba: medved Piki
> 92	535	555	ima naklonjenost	oseba: učitelj -[ima naklonjenost]-> vsebina: verzi
> 92	535	555	prebere	oseba: učitelj -[prebere]-> vsebina: verzi
> 92	535	533	kaznuje	oseba: učitelj -[kaznuje]-> skupina: učenci
> 92	535	482	prebere	oseba: učitelj -[prebere]-> predmet: spominska knjiga
> 92	482	73	pripada	predmet: spominska knjiga -[pripada]-> oseba: Timika
> 92	249	482	vpisuje se	skupina: medvedje -[vpisuje se]-> predmet: spominska knjiga
> 92	482	555	vsebuje	predmet: spominska knjiga -[vsebuje]-> vsebina: verzi
> 93	491	94	nariše	oseba: stari Marko -[nariše]-> risba: barko
> 93	535	187	listal	oseba: učitelj -[listal]-> predmet: knjiga
> 93	187	292	vsebuje	predmet: knjiga -[vsebuje]-> vsebina: nageljnov
> 93	187	588	vsebuje	predmet: knjiga -[vsebuje]-> vsebina: vrtnice
> 93	187	399	vsebuje	predmet: knjiga -[vsebuje]-> vsebina: pravljične hišice
> 93	32	276	izjavi	oseba: Marko Prvi -[izjavi]-> značilnost: modrost
> 93	535	277	razmišlja	oseba: učitelj -[razmišlja]-> značilnost: modrost Marka Prvega
> 94	12	554	piše	oseba: Filip -[piše]-> vsebina: verze
> 94	249	494	piše	skupina: medvedje -[piše]-> vsebina: stavek
> 94	535	58	prebere	oseba: učitelj -[prebere]-> predmet: Pikijeva knjižica
> 94	58	554	vsebuje	predmet: Pikijeva knjižica -[vsebuje]-> vsebina: verze
> 94	48	655	ima poklic	oseba: Piki -[ima poklic]-> poklic: šofer
> 94	18	468	ima poklic	oseba: Josip Jupiter -[ima poklic]-> poklic: skrbnik potnikov
> 95	535	381	izrazi upanje	oseba: učitelj -[izrazi upanje]-> značilnost: postajališča
> 95	535	103	preneha	oseba: učitelj -[preneha]-> dejanje: branje spominskih knjig
> 95	535	249	vpraša	oseba: učitelj -[vpraša]-> skupina: medvedje
> 95	249	535	odgovarjajo	skupina: medvedje -[odgovarjajo]-> oseba: učitelj
> 95	73	535	prosi	oseba: Timika -[prosi]-> oseba: učitelj
> 95	249	73	pridružujejo	skupina: medvedje -[pridružujejo]-> oseba: Timika
> 96	535	272	zahteva	oseba: učitelj -[zahteva]-> značilnost: mir
> 96	535	249	obljubljajo	oseba: učitelj -[obljubljajo]-> skupina: medvedje
> 96	249	535	obljubljajo	skupina: medvedje -[obljubljajo]-> oseba: učitelj
> 96	535	436	odhaja	oseba: učitelj -[odhaja]-> prostor: razred
> 96	150	483	ima	oseba: govorec -[ima]-> predmet: spominske knjige
> 96	535	512	izjavi	oseba: učitelj -[izjavi]-> značilnost: težava
> 96	150	360	obljubljajo	oseba: govorec -[obljubljajo]-> dejanje: pisanje
> 97	538	301	čaka	skupina: učitelj in medvedje -[čaka]-> pojem: nekaj
> 97	150	535	sodeluje	oseba: govorec -[sodeluje]-> oseba: učitelj
> 97	150	535	svetuje	oseba: govorec -[svetuje]-> oseba: učitelj
> 97	535	249	obljubljajo	oseba: učitelj -[obljubljajo]-> skupina: medvedje
> 97	150	528	sprejema	oseba: govorec -[sprejema]-> zvočni signal: trobentanje
> 98	150	535	obiskuje	oseba: govorec -[obiskuje]-> oseba: učitelj
> 98	535	150	pove	oseba: učitelj -[pove]-> oseba: govorec
> 98	535	150	povabi	oseba: učitelj -[povabi]-> oseba: govorec
> 98	254	426	sodelujejo	skupina: medvedji gasilci -[sodelujejo]-> dogodek: prva vaja
> 98	48	620	trobenta	oseba: Piki -[trobenta]-> zvočni signal: znamenje
> 98	254	637	ima opremo	skupina: medvedji gasilci -[ima opremo]-> predmet: čelade, vrv, gasilske sekirice
> 99	48	583	poravnava	oseba: Piki -[poravnava]-> skupina: vrsto
> 99	48	535	se predstavi	oseba: Piki -[se predstavi]-> oseba: učitelj
> 99	535	254	pozdravi	oseba: učitelj -[pozdravi]-> skupina: medvedji gasilci
> 99	254	535	odgovarjajo	skupina: medvedji gasilci -[odgovarjajo]-> oseba: učitelj
> 99	254	549	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: vaje
> 99	254	331	uporabljajo	skupina: medvedji gasilci -[uporabljajo]-> predmet: oprema
> 99	254	506	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: tekanje
> 99	254	410	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: preskakovanje ovir
> 99	254	322	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: odvijanje cevi
> 99	254	382	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: postavljanje lestev
> 99	254	467	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: skok s višine
> 100	48	141	vozi	oseba: Piki -[vozi]-> avto: gasilski avto
> 100	48	559	je	oseba: Piki -[je]-> poklic: višji gasilec
> 100	638	282	obvlada	skupina: četa -[obvlada]-> značilnost: motorizacijo
> 100	527	136	kliče	predmet: trobenta -[kliče]-> skupina: gasilce
> 100	139	630	izdaja zvok	predmet: gasilska sirena -[izdaja zvok]-> značilnost: zvok
> 100	154	110	cvili	del: gum gasilskega avta -[cvili]-> značilnost: cviljenje
> 101	64	578	predlaga	oseba: Poveljnik -[predlaga]-> aktivnost: vroče vaje
> 101	64	408	meni	oseba: Poveljnik -[meni]-> značilnost: preizkušanje znanja
> 101	638	142	prireja	skupina: četa -[prireja]-> dogodek: gasilski miting
> 101	142	43	ima naziv	dogodek: gasilski miting -[ima naziv]-> naziv: POŽAR V NBOTIČNIKU
> 101	287	317	je	skupina: moštvo -[je]-> značilnost: odlično izurjeno
> 102	526	138	utihne	predmet: trobent -[utihne]-> dogodek: gasilska akcija
> 102	141	194	odhiti	avto: gasilski avto -[odhiti]-> prostor: kraj požara
> 102	390	389	izda povelje	oseba: poveljnik -[izda povelje]-> ukaz: povelja
> 102	210	577	se pognajo	predmet: lestve -[se pognajo]-> prostor: vrhnja nadstropja
> 102	12	210	spleza	oseba: Filip -[spleza]-> predmet: lestve
> 102	13	325	rešujeta	skupina: Filip in Benjamin -[rešujeta]-> skupina: ogroženi prebivalci
> 102	299	565	ima	zgradba: nebotičnik -[ima]-> predmet: vodogrelec
> 103	48	283	pripravi	oseba: Piki -[pripravi]-> predmet: motorno brizgalno
> 103	48	104	uporabi	oseba: Piki -[uporabi]-> predmet: cev
> 103	48	109	usmeri	oseba: Piki -[usmeri]-> značilnost: curek
> 103	48	104	drži	oseba: Piki -[drži]-> predmet: cev
> 103	109	2	zadeva	značilnost: curek -[zadeva]-> oseba: Benjamin
> 103	109	12	zadeva	značilnost: curek -[zadeva]-> oseba: Filip
> 103	3	377	padeta	skupina: Benjamin in Filip -[padeta]-> prostor: ponjavo
> 104	48	137	pogasi	oseba: Piki -[pogasi]-> skupina: gasilci
> 104	390	283	izključi	oseba: poveljnik -[izključi]-> predmet: motorno brizgalno
> 104	390	366	razglasi	oseba: poveljnik -[razglasi]-> dogodek: pogasitev požara
> 104	137	331	pospravijo	skupina: gasilci -[pospravijo]-> predmet: oprema
> 104	48	527	zatrobenta	oseba: Piki -[zatrobenta]-> predmet: trobenta
> 104	137	123	odpeljejo se	skupina: gasilci -[odpeljejo se]-> prostor: domov
> 104	535	324	pove	oseba: učitelj -[pove]-> izkušnja: ognjeni krst
> 104	137	396	postanejo	skupina: gasilci -[postanejo]-> značilnost: pravi gasilci
> 105	48	562	pomisli	oseba: Piki -[pomisli]-> izkušnja: vodeni krst
> 105	390	140	razdeli	oseba: poveljnik -[razdeli]-> predmet: gasilske značke
> 105	73	437	pripne	oseba: Timika -[pripne]-> predmet: rdeč nagelj
> 105	56	451	sklene	oseba: Piki vrtnar -[sklene]-> aktivnost: saditev cvetic
> 105	77	575	prinaša	oseba: Učiteljeva mama -[prinaša]-> predmet: vrečice s čebulicami
> 106	574	636	vsebuje	predmet: vrečica -[vsebuje]-> predmet: čebulice
> 106	535	586	sodeluje	oseba: učitelj -[sodeluje]-> skupina: vrtnarski krožek
> 106	48	586	sodeluje	oseba: Piki -[sodeluje]-> skupina: vrtnarski krožek
> 106	535	376	postane	oseba: učitelj -[postane]-> poklic: pomočnik
> 106	48	587	postane	oseba: Piki -[postane]-> poklic: vrtnarski vajenec
> 106	221	584	gre	oseba: mama -[gre]-> prostor: vrtnarija
> 106	537	597	prebarvata	skupina: učitelj in Piki -[prebarvata]-> predmet: zabojčke
> 107	537	380	sklenejo	skupina: učitelj in Piki -[sklenejo]-> dogodek: posaditev čebulic
> 107	535	606	ima težavo	oseba: učitelj -[ima težavo]-> značilnost: zaspanje
> 107	48	606	ima težavo	oseba: Piki -[ima težavo]-> značilnost: zaspanje
> 107	535	303	vzdihne	oseba: učitelj -[vzdihne]-> značilnost: nesposobnost zaspati
> 107	48	303	zamomlja	oseba: Piki -[zamomlja]-> značilnost: nesposobnost zaspati
> 108	48	452	predlaga	oseba: Piki -[predlaga]-> aktivnost: saditev rož
> 108	535	59	odzove	oseba: učitelj -[odzove]-> predloga: Pikijeva predloga
> 108	535	515	ukazuje	oseba: učitelj -[ukazuje]-> značilnost: tišina
> 108	52	206	odplazita	skupina: Piki in učitelj -[odplazita]-> prostor: kuhinja
> 108	52	273	pogrinja	skupina: Piki in učitelj -[pogrinja]-> predmet: mizo

```sql
--TRUNCATE TABLE GRAPH_RELATIONS_STORY;
INSERT INTO GRAPH_RELATIONS_STORY(CHUNK_ID, HEAD_ID, TAIL_ID, RELATION, TEXT, CHUNK_DATA)
SELECT DISTINCT CHUNK_ID, head.ID as HEAD_ID,  tail.ID as TAIL_ID, s.relation, s.text, s.chunk_data
FROM GRAPH_RELATIONS_STG S
INNER JOIN  GRAPH_ENTITIES_STORY head ON head.ENTITY_NAME=s.head and head.ENTITY_TYPE = s.head_type
INNER JOIN  GRAPH_ENTITIES_STORY tail ON tail.ENTITY_NAME=s.tail and tail.ENTITY_TYPE = s.tail_type;

COMMIT;
```

> Query executed successfully. Affected rows : 1011

```sql
SELECT * FROM GRAPH_RELATIONS_STORY;
```

> ID	CHUNK_ID	HEAD_ID	TAIL_ID	RELATION	TEXT	CHUNK_DATA
> 1	33	535	244	sanja	oseba: učitelj -[sanja]-> oseba: medvedja mamica	»Dobro, da si mu pomežiknil,« je rekel učitelj in pobožal Pikija. Potem sta zaspala in sanjala o medvedji mamici, ki je naredila že toliko medvedkov, da bi jih lahko zložili v stolpnico. Piki piše pismo Učitelj rad piše pisma. Pošilja jih babici in dedku, tetam in stricem in včasih, kadar me ni doma, tudi meni. »Komu naj pa jaz pišem?« je nekega dne rekel Piki, ko je videl, da učitelj spet piše pismo.
> 2	35	50	23	živi	oseba: Piki Jakob -[živi]-> prostor: Ljubljana	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 3	37	50	99	stanuje	oseba: Piki Jakob -[stanuje]-> prostor: blok	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 4	38	50	395	ima poštno skrinjico	oseba: Piki Jakob -[ima poštno skrinjico]-> predmet: poštna skrinjica	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 5	41	48	535	se strinja	oseba: Piki -[se strinja]-> oseba: učitelj	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 6	41	535	332	vpraša	oseba: učitelj -[vpraša]-> oseba: otrok	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 7	42	48	611	ima zdravstveno knjižico	oseba: Piki -[ima zdravstveno knjižico]-> dokument: zdravstvena knjižica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 8	42	48	102	se sreča	oseba: Piki -[se sreča]-> oseba: bolniška sestra	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 9	42	48	632	čaka	oseba: Piki -[čaka]-> prostor: čakalnica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 10	43	48	498	sedel	oseba: Piki -[sedel]-> predmet: stol	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 11	46	48	626	ugrizne	oseba: Piki -[ugrizne]-> oseba: zobozdravnik	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 12	48	617	616	prejme	oseba: zmagovalec -[prejme]-> predmet: zlato medaljo	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 13	48	617	553	prejme	oseba: zmagovalec -[prejme]-> predmet: veliko hruško	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 14	49	251	429	tekajo	oseba: medvedji -[tekajo]-> prostor: pusto planjavo	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 15	50	251	172	tekajo	oseba: medvedji -[tekajo]-> prostor: južno gričevje	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 16	51	48	266	okleni	oseba: Piki -[okleni]-> prostor: mehki travnik	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 17	52	162	535	zavre	žival: hudi tiger -[zavre]-> oseba: učitelj	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 18	53	48	552	prejme	oseba: Piki -[prejme]-> predmet: velikansko hruško	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 19	54	535	67	odpelje	oseba: učitelj -[odpelje]-> prostor: Sora	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 20	54	48	70	zagleda	oseba: Piki -[zagleda]-> oseba: Stari Marko	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 21	56	48	218	uporablja	oseba: Piki -[uporablja]-> predmet: lonček za čaj	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 22	58	48	535	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: učitelj	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 23	59	535	48	meri	oseba: učitelj -[meri]-> oseba: Piki	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 24	60	48	190	se ohladi	oseba: Piki -[se ohladi]-> predmet: kopalna kada	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 25	61	535	48	vzame	oseba: učitelj -[vzame]-> oseba: Piki	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 26	62	150	535	se strinja	oseba: govorec -[se strinja]-> oseba: učitelj	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 27	64	48	362	vzame	oseba: Piki -[vzame]-> pripomoček: plavalni obroč	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 28	65	150	105	skriva	oseba: govorec -[skriva]-> predmet: cigarete	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 29	65	469	278	pripelje	skupina: skupina -[pripelje]-> prostor: morje	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 30	67	48	150	ima učitelja	oseba: Piki -[ima učitelja]-> oseba: govorec	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 31	68	48	629	sanja	oseba: Piki -[sanja]-> predmet: zvezek	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 32	70	48	419	vozi	oseba: Piki -[vozi]-> prostor: prometne ulice	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 33	71	150	48	ugovarjal	oseba: govorec -[ugovarjal]-> oseba: Piki	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 34	72	48	522	ponovil	oseba: Piki -[ponovil]-> značilnost: trditev	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 35	73	48	82	parkiral	oseba: Piki -[parkiral]-> predmet: avto	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 36	78	2	85	potovanje	oseba: Benjamin -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 37	78	31	85	potovanje	oseba: Marko Drugi -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 38	82	48	566	preneha	oseba: Piki -[preneha]-> dejavnost: voziti avtobusa	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 39	135	76	355	določil	oseba: Učitelj -[določil]-> značilnost: pevce, igralce, plesalce in recitatorje	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 40	136	48	563	postal	oseba: Piki -[postal]-> značilnost: vodja moškega pevskega zbora	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 41	138	48	354	izuril	oseba: Piki -[izuril]-> skupina: pevce	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 42	138	74	363	nastopil	skupina: Trio Marko -[nastopil]-> značilnost: ples	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 43	140	63	564	zlila	značilnost: Pomlad -[zlila]-> predmet: vodo	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 44	140	258	602	nastopil	skupina: medvedji pevski zbor -[nastopil]-> značilnost: zaključek	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 45	142	48	670	bi obiskal	oseba: Piki -[bi obiskal]-> prostor: Žužuja	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 46	143	535	11	predlagal	oseba: učitelj -[predlagal]-> etnična skupina: Eskimi	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 47	144	535	48	se pogovarja	oseba: učitelj -[se pogovarja]-> oseba: Piki	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 48	145	48	45	želi	oseba: Piki -[želi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 49	146	535	150	prosi	oseba: učitelj -[prosi]-> oseba: govorec	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 50	147	535	150	govori	oseba: učitelj -[govori]-> oseba: govorec	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 51	147	150	456	vozi	oseba: govorec -[vozi]-> predmet: sane	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 52	148	269	431	so	značilnost: mile jere -[so]-> značilnost: radovedneži	Čarovniki smo in učenci, kljukci in mile jere, radovedneži in poredneži. Da bi še dolgo tako potovali.
> 53	111	48	165	predlaga	oseba: Piki -[predlaga]-> dejanje: izkopavanje	»To vem tudi jaz,« je rekel učitelj, »a zdaj je važno, v katerem lončku so.« »Lahko jih spet izkopljeva,« je predlagal Piki. »Kaj se ti meša,« se je zgrozil učitelj. »Se bova že česa spomnila,« je rekel Piki pomirjevalno. Ko je drugo jutro mama stopila v kuhinjo, so jo presenetili zabojčki in lončki z napisanimi tablicami, ki so bile zataknjene v prst.
> 54	112	535	477	priznava	oseba: učitelj -[priznava]-> dejanje: sodelovanje z Pikijem	Na njih je pisalo: zvonček, rumeni krokus, rumeni tulipan, rožnata hijacinta in tako naprej. »Pri hiši imamo palčke,« je rekla mama, ko se je prikazal učitelj iz spalnice, »poglej, vse rože so posadili.« Učitelj je bil malo v zadregi. »Niso bili palčki,« je priznal, »ampak midva s Pikijem.« Sledil je izčrpen pogovor nočnem in dnevnem vrtnarstvu, o bedenju in spanju in še o marsičem drugem.
> 55	114	585	397	zatrjujeta	oseba: vrtnarja -[zatrjujeta]-> značilnost: pravilnost tablic	Vprašal sem učitelja, ali se mu ne zdi potrebno, da bi o enkratnem primeru, ko so iz tulipanove čebulice zrasli zvončki, obvestili vrtnarsko društvo. Učitelju se to ni zdelo potrebno ne zdaj ne pozneje, ko so se rožnate hijacinte spreminjale v modre, rumeni krokusi v bele in zvončki v rdeče tulipane. Vrtnarja sta vztrajno zatrjevala, da sta na tablice napisala prav tisto, kar je stalo na vrečkah iz katerih sta jemala čebulice. »Tu ima vmes svoje kremplje naš maček,« je rekel učitelj.
> 56	116	108	311	vabi	prostor: cirkus bežigrad -[vabi]-> oseba: obiskovalci	Na vežna vrata je obesil velik oglas: Cirkus BEŽIGRAD vabi k predstavi ob 16. uri. Nastopajo vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba. Pred nastopom ogled živalskega vrta. Vabljeni! Ogledal sem si vabilo in opozoril učitelja, naj se nikar ne šali z gledalci. »Če jih misliš povleči za os,« sem rekel, »gledalci ne bodo le žvižgali, ampak bodo tudi metali gnila jajca in paradižnike. Ob takih priložnostih je najljubša tarča direktor. Verjetno si to ti?«
> 57	118	514	328	so razporejeni	žival: tigri -[so razporejeni]-> prostor: okrog kletke	Lahko še pol ure vadiš. Jaz imam še opravke.« Ob pol štirih si je šlo občinstvo ogledat znamenite in redke živali, kakršnih nima noben cirkus na svetu. Medvedje so imeli vstop prost, ljudje pa smo plačali po en dinar. Živalski vrt ni bil velik, zato pa zanimiv. V središču je stala kletka z zelenima papagajema, okrog nje pa so pravilno razporejeni sedeli trije tigri in en črn lev. Največji tiger je bil precej podoben našemu mačku, druge tri zveri pa njegovim prijateljem iz hiše in bližnje soseščine.
> 58	118	293	226	je podoben	žival: največji tiger -[je podoben]-> žival: maček	Lahko še pol ure vadiš. Jaz imam še opravke.« Ob pol štirih si je šlo občinstvo ogledat znamenite in redke živali, kakršnih nima noben cirkus na svetu. Medvedje so imeli vstop prost, ljudje pa smo plačali po en dinar. Živalski vrt ni bil velik, zato pa zanimiv. V središču je stala kletka z zelenima papagajema, okrog nje pa so pravilno razporejeni sedeli trije tigri in en črn lev. Največji tiger je bil precej podoben našemu mačku, druge tri zveri pa njegovim prijateljem iz hiše in bližnje soseščine.
> 59	119	644	524	čuti	žival: črni lev -[čuti]-> značilnost: trdoto papagajevega kljuna	Sedeli so čisto pri miru in napeto opazovali, kaj se dogaja v kletki. Črni lev je nekajkrat stegnil taco, a jo je brž umaknil, ko je začutil trdoto papagajevega kljuna. Ker sem mu po nerodnosti stopil na rep, je divje zavreščal ter jo ubral iz živalskega vrta, za njim pa še dva njegova prijatelja. Zbežati je hotel tudi naš tiger, vendar ga je direktor pravočasno ujel in spravil na varno. Ogled živalskega vrta je bi s tem končan in občinstvo je odšlo na predstavo.
> 60	120	117	592	nastopa	oseba: direktor -[nastopa]-> vloga: vrvohodec	Na začetku je direktor v vlogi cirkuške godbe odigral na blokﬂavto Koračnico palčkov, ki je vsem zelo ugajala in jo je moral ponoviti. Nato je nastopil kot vrvohodec in je z odprtim dežnikom dvakrat prehodil stranice pri posteljah, ne da bi padel na tla. Potem so nas zabavali klovni: Debeli Bongo in Suhi Grintež, Mali Makec in Dolgi Jakec, Nemi Lukec in Lapasti Kljukec. Bili so našemljeni v obleke, ki so se mi zdele znane iz naše omare. Sledila je točka velikega žonglerja Lovikrogle.
> 61	120	28	8	sodeluje	oseba: Mali Makec -[sodeluje]-> oseba: Dolgi Jakec	Na začetku je direktor v vlogi cirkuške godbe odigral na blokﬂavto Koračnico palčkov, ki je vsem zelo ugajala in jo je moral ponoviti. Nato je nastopil kot vrvohodec in je z odprtim dežnikom dvakrat prehodil stranice pri posteljah, ne da bi padel na tla. Potem so nas zabavali klovni: Debeli Bongo in Suhi Grintež, Mali Makec in Dolgi Jakec, Nemi Lukec in Lapasti Kljukec. Bili so našemljeni v obleke, ki so se mi zdele znane iz naše omare. Sledila je točka velikega žonglerja Lovikrogle.
> 62	123	55	337	postane	oseba: Piki padalec -[postane]-> poklic: padalec	Po treh ponovitvah so mu gledalci burno zaploskali, umetnik pa se je šel hladit na balkon. Ko smo zapuščali cirkuški šotor, je godba igrala »Na planincah luštno biti,« gledalci pa so zapeli kitico »Pastirica žgance kuha, notri pade ena muha.« Medtem se je zjasnilo in tako smo z imenitne predstave lahko odšli na sprehod. Piki padalec Piki je postal padalec.
> 63	124	48	97	ima vtis	oseba: Piki -[ima vtis]-> predmet: beli mehurčki	Seveda ni treba misliti, da mu je spodrsnilo na ledu ali da se je spotaknil na cesti, tudi s kolesa ni padel, še manj pa pri matematiki. Piki je postal član padalskega društva. Nekega večera smo na televiziji gledali ﬁlm o padalcih. Beli mehurčki, ki so vreli iz letal, se počasi večali ter slednjič kot ogromne napihnjene buče pristali na tleh, so bili Pikiju zelo všeč.
> 64	125	535	339	postane	oseba: učitelj -[postane]-> poklic: padalski polkovnik	Rekel je, da bi padalci tudi pri nas lahko skakali z balkona ali terase in, ker je bil učitelj za to, sta ustanovila padalsko društvo. Medvedje se za novi šport niso preveč zanimali. Razen Pikija so se prijavili samo še Josip Jupiter, Stari Marko in Filip. Mama jim je iz stare rjuhe sešila padala, učitelj, ki je postal padalski polkovnik, pa je sestavil vadbeni urnik. Prva vaja se je imenovala »pristanek«.
> 65	126	371	414	povabi	oseba: polkovnik -[povabi]-> oseba: pripovedovalec	Na njej so pripravniki v travi za blokom vadili žabje skoke, počepe in prevale. Čez teden dni so prešli na vajo »polet«. Oblečeni v padalske »telovnike« so na terasi ure in ure bingljali na vrveh za sušenje perila. Na koncu je sledil še preskus vrtoglavice. Polkovnik je bodoče padalce posadil v centrifugo in jih tako prevrtel, da so prišli ven čisto ploščati. S to vajo se je tečaj končal in za naslednji dan so bili napovedani skoki. Polkovnik me je povabil na prireditev.
> 66	134	36	400	ni imela	prostor: Medvedja šola -[ni imela]-> značilnost: praznika	Polkovnik mi je pojasnil, da pomeni PP prav tako POBIRALEC PADALCEV. Ta naslov sem spreje, nakar smo vsi zadovoljni odšli na PP ali popoldanski počitek. Praznik Medvedja šola dolgo ni imela svojega praznika. Učitelj je zbiral predloge in tehtal dneve, vendar je v vsakem našel kakšno napako. Eden je bil preblizu novega leta, drugi preblizu počitnic, tretjega so praznovali že kje drugje. Ko je že skoraj obupal, je prišel k njemu Piki in rekel: »Zdi se mi, da imam dober predlog.«
> 67	3	535	14	spiva z	oseba: učitelj -[spiva z]-> oseba: Floki	Z njim se peljejo tudi drugi medvedi in vseh skupaj je za cel medvedji avtobus. Dvema ali trem je ime Marko. Eden je Filip in majhni medvedki je ime Timika. Potem so tukaj še Josip Jupiter, Benjamin in Floki, ki sicer ni medved, ampak pes, vendar hodi v medvedjo šolo, ker posebne pasje šole še nimamo. Z učiteljem spiva v isti sobi in zato je Piki včasih tudi leteči medved. Ko se učitelj zjutraj zbudi, pogleda, ali jaz še spim, in mi vrže medveda na glavo.
> 68	4	48	155	prileti	oseba: Piki -[prileti]-> predmet: helikopter	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.
> 69	5	48	46	bil je	oseba: Piki -[bil je]-> prostor: Pariz	V sanjah se včasih pogovarjava po francosko. Pravi, da je bil nekoč v Parizu in da tam medvede kličejo Žužu. Prav rad mu verjamem, vendar se strinjava, da je Piki lepše ime. Mogoče me bo Piki naučil medvedjega jezika. O tem se še nisva pogovarjala, ker sva oba zelo zaposlena. Piki se mora učiti za šolo, jaz pa moram pisati knjige. Francoska solata Imeli smo goste in učiteljeva mama je pripravljala razne imenitne jedi. Takih jedi ne jemo vsak dan in zato je učitelj do njih nezaupljiv.
> 70	7	535	297	ima mnenje	oseba: učitelj -[ima mnenje]-> značilnost: ne bom jedel	»Samo malo poskusi,« je rekla mama, »samo eno žličko.« Učitelj je odgovoril: »Take čudne jedi mi niso všeč. Ne maram jih.« Mama je vztrajala: »Moraš se navaditi tudi na nove jedi.« Učitelj je bil drugačnega mnenja in je ponovil: »Ne bom.« Mama ni popustila: »Samo eno žličko. Saj ni strup.« Učitelj pa je rekel: »Je. Če to pojem, bom umrl.«
> 71	9	535	221	molči	oseba: učitelj -[molči]-> oseba: mama	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 72	14	226	678	izdaja zvok	žival: maček -[izdaja zvok]-> značilnost: žvižganje	Ozrl sem se skozi okno, pa sem zagledal mačka.« »To se ti je sanjalo,« je rekel učitelj. »Našega mačka poznam. Marsikaj zna, žvižga pa zagotovo ne.« Piki je skomignil z rameni: »Jaz nisem kriv, če je včeraj žvižgal.« »Sedi,« je strogo rekel učitelj. »Dovolj je šale. Če jaz rečem, da mačke ne žvižgajo, potem ne žvižgajo, razumeš?« »Razumem, da ne žvižgajo,« je rekel Piki in sedel.
> 73	14	535	232	trdi	oseba: učitelj -[trdi]-> značilnost: mačke ne žvižgajo	Ozrl sem se skozi okno, pa sem zagledal mačka.« »To se ti je sanjalo,« je rekel učitelj. »Našega mačka poznam. Marsikaj zna, žvižga pa zagotovo ne.« Piki je skomignil z rameni: »Jaz nisem kriv, če je včeraj žvižgal.« »Sedi,« je strogo rekel učitelj. »Dovolj je šale. Če jaz rečem, da mačke ne žvižgajo, potem ne žvižgajo, razumeš?« »Razumem, da ne žvižgajo,« je rekel Piki in sedel.
> 74	15	535	30	govori	oseba: učitelj -[govori]-> oseba: Marko	»Nadaljujmo,« je rekel učitelj. »Marko, povej …« Tedaj je pozvonilo. Učitelj je prenehal sredi stavka. Potrkal je s svinčnikom po mizi in rekel: »Takoj se vrnem. Med tem ponavljajte.« Medvedje so se zagledali v zvezke, učitelj pa je odšel v vežo. Previdno, komaj za dlan široko je odprl vrata in pokukal ven. Zunaj je stal moški iz sosednega stopnišča. »Je očka doma?« je vprašal. Učitelj je odkimal. »Pa mama?«
> 75	16	535	230	ima	oseba: učitelj -[ima]-> žival: mačka	»Tudi ne,« je rekel učitelj. »Hja,« je rekel moški in strogo premeril učitelja. »Mačka pa imate, kaj?« »Ja, imamo,« je rekel učitelj. »Pa veš kaj ta maček dela?« je jezno vprašal moški »Ne,« je plaho odkimal učitelj. »Potem ti bom jaz povedal,« je rekel moški. »Ptičke ubija. Včeraj je požrl našega kanarčka. Povej očku in mami, da je bilo to prvič in zadnjič.
> 76	16	285	535	pove	oseba: moški -[pove]-> oseba: učitelj	»Tudi ne,« je rekel učitelj. »Hja,« je rekel moški in strogo premeril učitelja. »Mačka pa imate, kaj?« »Ja, imamo,« je rekel učitelj. »Pa veš kaj ta maček dela?« je jezno vprašal moški »Ne,« je plaho odkimal učitelj. »Potem ti bom jaz povedal,« je rekel moški. »Ptičke ubija. Včeraj je požrl našega kanarčka. Povej očku in mami, da je bilo to prvič in zadnjič.
> 77	17	231	268	mijavkajo	žival: mačke -[mijavkajo]-> značilnost: mijavkanje	Če se še enkrat prikaže, ga bom predelal v klobase. Razumeš?« Učitelj je pokimal in zaprl vrata. Vrnil se je v razred in rekel: »Za danes smo končali. Lahko greste. Piki, ti pa malo počakaj.« Ko so medvedje odšli, je učitelj obstal pred Pikijem. »Kot sem rekel,« je začel, »mačke mijavkajo. Vendar pa se zgodi, da ta ali ona včasih tudi zažvižga, Ampak naj to ostane med nama.«
> 78	18	48	647	igra	oseba: Piki -[igra]-> igra: šah	Piki je pokimal in s tem je bila zadeva v medvedji šoli opravljena. Jaz pa sem se moral sosedu opravičiti in mu kupiti novega kanarčka. Zdaj premišljujem, ali ne bi še našemu mačku kupil nagobčnika. Piki igra šah Učitelj je rekel Pikiju: »Se greva šah?« Piki je kot ubogljiv medved pokimal. Postavila sta ﬁgure in učitelj je rekel: »Če se boš naučil dobro igrati, boš postal še medvedji šahovski velemojster.« Piki je spet pokimal.
> 79	18	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj	Piki je pokimal in s tem je bila zadeva v medvedji šoli opravljena. Jaz pa sem se moral sosedu opravičiti in mu kupiti novega kanarčka. Zdaj premišljujem, ali ne bi še našemu mačku kupil nagobčnika. Piki igra šah Učitelj je rekel Pikiju: »Se greva šah?« Piki je kot ubogljiv medved pokimal. Postavila sta ﬁgure in učitelj je rekel: »Če se boš naučil dobro igrati, boš postal še medvedji šahovski velemojster.« Piki je spet pokimal.
> 80	19	535	186	napravi potezo	oseba: učitelj -[napravi potezo]-> predmet: kmet	Učitelj je imel bele ﬁgure in je potegnil kmeta pred kraljem za dve polji naprej. Piki je z druge strani napravil enako potezo. Potem je učitelj povlekel lovca in tudi Piki je povlekel lovca. Učitelj je skočil s konjem in tudi Piki je skočil s konjem. »Nikar me ne posnemaj,« je rekel učitelj, »če ne, boš kmalu izgubil.« Igrala sta naprej in oba naredila malo rošado. Potem je učitelj vzel Pikiju kmeta. Piki se je globoko zamislil.
> 81	19	535	186	vzame	oseba: učitelj -[vzame]-> predmet: kmet	Učitelj je imel bele ﬁgure in je potegnil kmeta pred kraljem za dve polji naprej. Piki je z druge strani napravil enako potezo. Potem je učitelj povlekel lovca in tudi Piki je povlekel lovca. Učitelj je skočil s konjem in tudi Piki je skočil s konjem. »Nikar me ne posnemaj,« je rekel učitelj, »če ne, boš kmalu izgubil.« Igrala sta naprej in oba naredila malo rošado. Potem je učitelj vzel Pikiju kmeta. Piki se je globoko zamislil.
> 82	20	48	642	postavi	oseba: Piki -[postavi]-> predmet: črni kmet	Učitelj je postal živčen: »Kaj pa toliko premišljuješ, požri kmeta, pa konec.« Piki se je malo obotavljal, potem pa vprašal: »Misliš resno?« »Seveda,« je rekel učitelj. »No, daj že.« Piki je s tresočo se taco vzel belega kmeta in postavil črnega na njegovo polje. Učitelj se je zagledal v šahovnico, Piki pa je pogledal kmeta, ki ga je držal v taci, potem pa skomignil z rameni in ga po tihem požrl.
> 83	20	535	649	gleda	oseba: učitelj -[gleda]-> predmet: šahovnica	Učitelj je postal živčen: »Kaj pa toliko premišljuješ, požri kmeta, pa konec.« Piki se je malo obotavljal, potem pa vprašal: »Misliš resno?« »Seveda,« je rekel učitelj. »No, daj že.« Piki je s tresočo se taco vzel belega kmeta in postavil črnega na njegovo polje. Učitelj se je zagledal v šahovnico, Piki pa je pogledal kmeta, ki ga je držal v taci, potem pa skomignil z rameni in ga po tihem požrl.
> 84	24	48	95	požre	oseba: Piki -[požre]-> figurka: bele figure	Skril si ga. Sram te bodi. Tak šahist! Takoj ga daj sem.« »Ne morem,« je rekel Piki. »Kako ne moreš?« je vprašal učitelj »Požrl sem ga,« je priznal Piki. »Žreš lahko samo nasprotnikove ﬁgure, ne svojih,« je rekel učitelj. »Kljub vsemu si torej mat. Greva še eno partijo. Zdaj imaš ti bele.« »Nimam jih,« je rekel Piki. »Kako jih nimaš?« »Požrl sem jih.
> 85	26	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj	« In potem sta oba prišla k meni. Medvedja mamica Nekega večera, ko sta ležala v postelji in si kakor ponavadi pripovedovala zgodbe, je učitelj vprašal Pikija: »Ali veš kako si prišel na svet?« »Vem,« je odgovoril Piki. »Naredila me je medvedja mamica.« »Ne reče se 'naredila' ampak 'rodila', če kaj vem,« je rekel učitelj. »Že mogoče,« je odgovoril Piki, »ampak mene je zagotovo naredila. Pa ne samo mene.
> 86	26	48	244	ima izvor	oseba: Piki -[ima izvor]-> oseba: medvedja mamica	« In potem sta oba prišla k meni. Medvedja mamica Nekega večera, ko sta ležala v postelji in si kakor ponavadi pripovedovala zgodbe, je učitelj vprašal Pikija: »Ali veš kako si prišel na svet?« »Vem,« je odgovoril Piki. »Naredila me je medvedja mamica.« »Ne reče se 'naredila' ampak 'rodila', če kaj vem,« je rekel učitelj. »Že mogoče,« je odgovoril Piki, »ampak mene je zagotovo naredila. Pa ne samo mene.
> 87	28	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki	»Ko sem bil jaz na vrsti, nas je bilo pač trideset. Je že bil tak mesec. Prav dobro vem, da nas je bilo trideset, ker je mene naredila prvega in sem imel čas šteti. Imela je krojne pole za velike in srednje in majhne medvedke. Zame je izbrala posebno lep kroj. Razen tega mi je prišila rjav in bel pliš. Takega kožuha nima vsak medvedek. Po večini so rumeni, kot da bi bili levi in ne medvedi. Si že kdaj videl rjavega leva?«
> 88	28	244	202	ima orodje	oseba: medvedja mamica -[ima orodje]-> orodje: krojne pole	»Ko sem bil jaz na vrsti, nas je bilo pač trideset. Je že bil tak mesec. Prav dobro vem, da nas je bilo trideset, ker je mene naredila prvega in sem imel čas šteti. Imela je krojne pole za velike in srednje in majhne medvedke. Zame je izbrala posebno lep kroj. Razen tega mi je prišila rjav in bel pliš. Takega kožuha nima vsak medvedek. Po večini so rumeni, kot da bi bili levi in ne medvedi. Si že kdaj videl rjavega leva?«
> 89	29	244	652	deluje	oseba: medvedja mamica -[deluje]-> orodje: škarje	»Ne,« je rekel učitelj. »Tisti v živalskem vrtu je rumen. »No, vidiš,« je nadaljeval Piki. »Sicer pa me levi ne zanimajo. Govoriva o medvedji mamici. Mene je naphala z vato. Zato sem tako mehek. Samo Nekaj nas je bilo takih. Drugi so bili nabasani z morsko travo ali žagovino. Sedel sem na polici in jo opazoval. Kako je samo znala sukati škarje, ko je rezala blago za podlogo in kožušček.
> 90	30	244	550	ima material	oseba: medvedja mamica -[ima material]-> material: vata	Švrk, švrk, švrk -telo, švrk, švrk -roke, švrk, švrk -noge, pa še švrc. Švrc -ušesa in kožuh je bil pripravljen. Potem je v podlogo nabasala vato ali morsko travo, prišila nanjo kožuh, pripela k telesu noge, roke in glavo, na glavo pa še smrček, ušesa in oči. Ta ali oni medvedek je dobil tudi pentljo okrog vratu. Ko je bil sešit, si ga je medvedja mamica še enkrat skrbno ogledala, ga pokrtačila in postavila na polico.
> 91	83	247	177	kupujejo	oseba: medvedje -[kupujejo]-> predmet: kariraste čepice	Medvedje prejšnji večer od veselja sploh niso mogli zaspati, Boksali in ščipali so se pod odejo, tako da sta Floki in Benjamin celo padla iz postelje. Učitelj je bil na dan otvoritve zelo zaposlen, medvedje pa so se lišpali in krtačili, kot da bi šli na gostijo. Mnogi so si kupili kariraste čepice, Timika pa je dišala, kot bi padla v steklenico s parfumom. Ob treh se je prireditev končno začela. Lepo okrašeni prostore v dnevni sobi je bil razdeljen na sejmišče in zabavišče.
> 92	85	48	672	ogleduje	oseba: Piki -[ogleduje]-> predmet: železnica	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 93	85	672	405	teče	predmet: železnica -[teče]-> prostor: predori	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 94	88	19	153	pelje	oseba: Jupiter -[pelje]-> značilnost: grmenje in bliskanje	»Ko te poboža,« je rekel Piki, »zgrabi z vso močjo. »Zanesi se name,« je zamrmral Jupiter. Spet sta se peljala skoz grmenje in bliskanje in napeto čakala na pravi trenutek. V Dvorani smrti sta potem zagrabila. V tem hipu se je Hiša strahov prislužila svoje ime. Smrt je strašno zarjula, se iztrgala Pikiju in Jupitru iz rok ter se skoz streho pognala iz hiše.
> 95	91	535	483	zadržal	oseba: učitelj -[zadržal]-> predmet: spominske knjige	Potem je nabral po razredu osem spominskih knjig in jih zadržal za nedoločen čas. Medtem ko so poparjeni otroci prepisovali s table stavek »Med poukom mora biti spominska knjiga v torbi«, je učitelj sedel za mizo in listal po zaplenjenem blagu. Najprej mu je prišla pod roke Flokijeva knjiga. V njej je bil en sam zapis. Poleg lepo pobarvanega medveda so stale vrstice: Lep in mlad je na tej sliki tvoj prijatelj medved Piki tudi ko bo grd in star, ne pozabi ga nikdar.
> 96	91	603	237	opisuje	vsebina: zapis -[opisuje]-> oseba: medved Piki	Potem je nabral po razredu osem spominskih knjig in jih zadržal za nedoločen čas. Medtem ko so poparjeni otroci prepisovali s table stavek »Med poukom mora biti spominska knjiga v torbi«, je učitelj sedel za mizo in listal po zaplenjenem blagu. Najprej mu je prišla pod roke Flokijeva knjiga. V njej je bil en sam zapis. Poleg lepo pobarvanega medveda so stale vrstice: Lep in mlad je na tej sliki tvoj prijatelj medved Piki tudi ko bo grd in star, ne pozabi ga nikdar.
> 97	92	535	555	ima naklonjenost	oseba: učitelj -[ima naklonjenost]-> vsebina: verzi	Učitelju so bili verzi všeč, dvakrat jih je prebral in malo je manjkalo, pa bi Pikija pohvalil. Vendar se je še pravi čas spomnil, da je učence kaznoval, in tako je z resnim obrazom segel po drugi spominski knjigi. Bila je vezana v rdeče usnje in na platnicah je pisalo Timika. Knjiga je bila skoraj polna, nekateri medvedje so se vpisali celo po večkrat. Na začetku je bila okorno narisana ladjica, zraven pa verzi: Nisem pesnik ne risar, kaj ti naj poklonim v dar?
> 98	96	150	360	obljubljajo	oseba: govorec -[obljubljajo]-> dejanje: pisanje	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 99	97	150	535	sodeluje	oseba: govorec -[sodeluje]-> oseba: učitelj	Bojim se, da bodo morali učitelj in medvedje še malo počakati. Gasilska četa Pozimi sva z učiteljem kurila peči. »Pri kurjavi moraš biti previden,« sem rekel, »kajti če skoči ogenj iz peči, lahko zgorita parket in pohištvo, nazadnje pa še hiša.« Učitelj je prikimal in rekel: »Opozoriti bom moral tudi medvede.« Ko sem tistega dne po kosilu malo zadremal, se je iz kuhinje kar na lepem oglasilo živahno trobentanje.
> 100	98	535	150	povabi	oseba: učitelj -[povabi]-> oseba: govorec	Šel sem pogledat, kaj se dogaja, in učitelj mi je povedal, da so pravkar ustanovili medvedjo gasilsko četo. Povabil me je, naj bom navzoč pri prvi vaji, češ da bo to spodbudno za mlade gasilce. Ti so na znamenje trobentača Pikija že tekli od vseh strani in se, kot bi trenil, postavili v vrsto. Vsak je imel na glavi čelado, za pasom vrv, ob boku pa gasilsko sekirico.
> 101	98	254	426	sodelujejo	skupina: medvedji gasilci -[sodelujejo]-> dogodek: prva vaja	Šel sem pogledat, kaj se dogaja, in učitelj mi je povedal, da so pravkar ustanovili medvedjo gasilsko četo. Povabil me je, naj bom navzoč pri prvi vaji, češ da bo to spodbudno za mlade gasilce. Ti so na znamenje trobentača Pikija že tekli od vseh strani in se, kot bi trenil, postavili v vrsto. Vsak je imel na glavi čelado, za pasom vrv, ob boku pa gasilsko sekirico.
> 102	99	48	535	se predstavi	oseba: Piki -[se predstavi]-> oseba: učitelj	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 103	100	139	630	izdaja zvok	predmet: gasilska sirena -[izdaja zvok]-> značilnost: zvok	Bili so zelo požrtvovalni in zato sem jih po končani vaji s poveljnikom vred povabil na malinovec. Poslej je trobenta vsak dan po kosilu klicala gasilce »na pomoč«. Četa je kmalu obvlada tudi motorizacij in zvokom trobente so se pridružili zvoki gasilske sirene in cviljenje gum gasilskega avta, ki ga je višji gasilec Piki vozil na »kraj požara«.
> 104	102	390	389	izda povelje	oseba: poveljnik -[izda povelje]-> ukaz: povelja	Trobent je komaj dobro utihnila, ko je že pridrvel izza ovinka gasilski avto in s presunljivim »goo-rii, goo-rii« odhitel na kraj požara. Vrstila so se povelja: »Sestavite lestve! Razvijte cevi! Priključite vodo!« Za nebotičnik je služil veliki vodogrelec v kotu kopalnice. Lestve so se pognale do vrhnjih nadstropij, po njih sta splezala Filip in Benjamin ter začela reševati »ogrožene prebivalce«.
> 105	102	12	210	spleza	oseba: Filip -[spleza]-> predmet: lestve	Trobent je komaj dobro utihnila, ko je že pridrvel izza ovinka gasilski avto in s presunljivim »goo-rii, goo-rii« odhitel na kraj požara. Vrstila so se povelja: »Sestavite lestve! Razvijte cevi! Priključite vodo!« Za nebotičnik je služil veliki vodogrelec v kotu kopalnice. Lestve so se pognale do vrhnjih nadstropij, po njih sta splezala Filip in Benjamin ter začela reševati »ogrožene prebivalce«.
> 106	105	73	437	pripne	oseba: Timika -[pripne]-> predmet: rdeč nagelj	»Lahko bi se reklo tudi vodeni krst,« je pomislil Piki, vendar zaradi še zmeraj jeznih gasilcev tega ni povedal na glas. Po govoru je poveljnik razdelil gasilske značke, Timika pa je vsakemu pripela na prsi rdeč nagelj. Od takrat se pri nas več ne bojimo požarov. Piki vrtnar Učiteljeva mama je sklenila, da bo posadila v lončke nekaj spomladanskih cvetic. Iz semenarne je prinesla vrečice s čebulicami različnih velikosti.
> 107	106	48	586	sodeluje	oseba: Piki -[sodeluje]-> skupina: vrtnarski krožek	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 108	106	535	376	postane	oseba: učitelj -[postane]-> poklic: pomočnik	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 109	106	48	587	postane	oseba: Piki -[postane]-> poklic: vrtnarski vajenec	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 110	107	48	303	zamomlja	oseba: Piki -[zamomlja]-> značilnost: nesposobnost zaspati	Sklenili so, da bodo čebulice posadili v soboto dopoldne, ko bodo prosti in ne bodo imeli drugih skrbi. Tisto noč je bilo zadušljivo, tako da učitelj in Piki dolgo nista mogla zaspati. Dvakrat sta šla pit slatino, pa ni nič pomagalo. Ko smo vsi drugi že spali, sta se še zmeraj premetavala po postelji. »Ne morem in ne morem zaspati,« je vzdihnil učitelj. »Jaz tudi ne,« je zamomljal Piki in si obrisal potno čelo.
> 111	31	244	430	ima lastnost	oseba: medvedja mamica -[ima lastnost]-> značilnost: rada	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 112	32	288	264	prezema	oseba: možakar -[prezema]-> predmet: medvedki	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 113	32	264	216	ima lastnost	predmet: medvedki -[ima lastnost]-> značilnost: listek	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 114	36	48	33	piše	oseba: Piki -[piše]-> oseba: Marmeladov	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 115	36	48	667	prejme pismo	oseba: Piki -[prejme pismo]-> oseba: Žužu	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 116	36	667	267	vozi	oseba: Žužu -[vozi]-> predmet: metro	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 117	37	394	499	pozvonil	oseba: poštar -[pozvonil]-> prostor: stopnišče	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 118	39	48	625	ima zobobol	oseba: Piki -[ima zobobol]-> značilnost: zobobol	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 119	40	48	449	obvezan z	oseba: Piki -[obvezan z]-> predmet: ruto	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 120	41	48	626	potrpi	oseba: Piki -[potrpi]-> oseba: zobozdravnik	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 121	42	50	625	ima težavo	oseba: Piki Jakob -[ima težavo]-> značilnost: zobobol	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 122	46	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 123	46	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 124	46	535	414	opozarja	oseba: učitelj -[opozarja]-> oseba: pripovedovalec	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 125	48	535	418	pripravlja	oseba: učitelj -[pripravlja]-> prostor: proga	»Zmagovalec bo dobil zlato medaljo in veliko hruško,« je rekel. »Kot na olimpiadi,« je vzdihnila Timika. »Na olimpiadi ne delijo hrušk,« je rekel Piki in se zarežal. Timika ga je grdo pogledala in malo je manjkalo, pa bi mu pokazala jezik. Medtem je učitelj pripravil progo. Start in cilj sta bila na zeleni livadi ali po domače v kuhinji. Medvedje so se postavili v vrsto in ko je učitelj zaklical »zdaj«, so se pognali v tek.
> 126	49	535	125	postavi	oseba: učitelj -[postavi]-> predmet: drevesa	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 127	49	12	444	pade	oseba: Filip -[pade]-> prostor: ribnik	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 128	50	48	383	skoke	oseba: Piki -[skoke]-> predmet: postelja	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 129	51	48	226	spozna	oseba: Piki -[spozna]-> žival: maček	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 130	52	535	327	zapre	oseba: učitelj -[zapre]-> predmet: okna	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 131	53	507	48	zaploskajo	oseba: tekmovalci -[zaploskajo]-> oseba: Piki	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 132	53	48	513	jezdi	oseba: Piki -[jezdi]-> žival: tiger	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 133	54	48	582	ima	oseba: Piki -[ima]-> zdravstvena stanja: vročino	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 134	59	48	509	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: telesna temperatura	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 135	63	535	226	prosi	oseba: učitelj -[prosi]-> žival: maček	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 136	66	48	601	je	oseba: Piki -[je]-> čustvo: zadovoljen	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 137	66	48	443	lovi	oseba: Piki -[lovi]-> žival: ribe	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 138	66	48	472	se veseli	oseba: Piki -[se veseli]-> pojav: slana voda	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 139	66	48	570	obiskuje	oseba: Piki -[obiskuje]-> učilnica: vozniška šola	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 140	69	535	48	razložil	oseba: učitelj -[razložil]-> oseba: Piki	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 141	69	48	481	naučil	oseba: Piki -[naučil]-> značilnost: speljevanja in ustavljanja	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 142	70	48	519	sreča	oseba: Piki -[sreča]-> predmet: tovornjak	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 143	71	48	121	prižgal	oseba: Piki -[prižgal]-> značilnost: dolge luči	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 144	74	48	281	upravlja	oseba: Piki -[upravlja]-> predmet: moterne vozilo	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 145	75	18	372	ugotovil	oseba: Josip Jupiter -[ugotovil]-> značilnost: pomanjkanje	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 146	76	386	189	izstopali	oseba: potniki -[izstopali]-> prostor: končna postaja	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 147	77	660	26	izstopili	oseba: šolarji -[izstopili]-> prostor: MEDVEDJA ŠOLA	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 148	77	2	18	odgovoril	oseba: Benjamin -[odgovoril]-> oseba: Josip Jupiter	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 149	78	18	2	govori	oseba: Josip Jupiter -[govori]-> oseba: Benjamin	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 150	80	85	229	trči	prostor: avtobus -[trči]-> predmet: mačji rep	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 151	81	48	518	pomaga	oseba: Piki -[pomaga]-> oseba: tovariš	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 152	81	560	412	prekinja	oseba: višji policijski inšpektor -[prekinja]-> dogodek: pretep	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 153	81	560	199	naloži kazni	oseba: višji policijski inšpektor -[naloži kazni]-> oseba: krivci	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 154	82	37	654	vrnejo	oseba: Medvedje -[vrnejo]-> značilnost: škodo	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 155	82	16	69	daje	oseba: Govorec -[daje]-> oseba: Sprevodnik	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 156	82	69	150	obljublja	oseba: Sprevodnik -[obljublja]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 157	139	143	378	zahtevali	skupina: gledalci -[zahtevali]-> značilnost: ponovitev	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 158	140	439	417	nastopili	skupina: recitatorji -[nastopili]-> značilnost: prizor	Prizor je bil v verzih in na koncu vsake kitice je Pomlad zaklicala: »Oj vstani, vstani, Domberdan!« leni Domberdan je odgovarjal: »Oh, ko sem pa tako zaspan!« Ker besede niso zalegle, si je Pomlad pomagala s kanglico vode, ki jo je zlila Domberdanu na glavo. Ta prizor se je mladim gledalcem zdel zelo smešen. Nastopilo je še nekaj recitatorjev, za konec pa je še enkrat nastopil medvedji pevski zbor.
> 159	141	308	20	vsebujejo	značilnost: nove pesmi -[vsebujejo]-> značilnost: Ko medved zjutraj v šolo gre	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 160	143	48	460	bi rad videl	oseba: Piki -[bi rad videl]-> žival: severne medvede	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 161	144	48	673	ima željo	oseba: Piki -[ima željo]-> žival: žirafe	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 162	145	535	45	želi	oseba: učitelj -[želi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 163	145	150	45	trdi	oseba: govorec -[trdi]-> mesto: Pariz	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 164	147	535	48	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Piki	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 165	109	52	453	delata	skupina: Piki in učitelj -[delata]-> aktivnost: saditev čebulic	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 166	110	48	541	odzove	oseba: Piki -[odzove]-> značilnost: učiteljeva skrb	Malo utrujena, a zadovoljna sta sedla na klop in gledala lepo pobarvane zabojčke in lončke. Nenadoma pa je učitelj vzkliknil: »Ojej, pozabila sva napisati, kam sva kaj posadila.« »Kaj ni vseeno?« je rekel Piki. »Ni. Mama bo vprašala, kakšne rože so kje.« »Še zmeraj lahko napiševa,« je rekel Piki. »Jaz se spomnim, v katerih vrečicah so bile čebulice.«
> 167	111	221	599	opazi	oseba: mama -[opazi]-> predmet: zabojčki in lončki	»To vem tudi jaz,« je rekel učitelj, »a zdaj je važno, v katerem lončku so.« »Lahko jih spet izkopljeva,« je predlagal Piki. »Kaj se ti meša,« se je zgrozil učitelj. »Se bova že česa spomnila,« je rekel Piki pomirjevalno. Ko je drugo jutro mama stopila v kuhinjo, so jo presenetili zabojčki in lončki z napisanimi tablicami, ki so bile zataknjene v prst.
> 168	112	221	535	govori	oseba: mama -[govori]-> oseba: učitelj	Na njih je pisalo: zvonček, rumeni krokus, rumeni tulipan, rožnata hijacinta in tako naprej. »Pri hiši imamo palčke,« je rekla mama, ko se je prikazal učitelj iz spalnice, »poglej, vse rože so posadili.« Učitelj je bil malo v zadregi. »Niso bili palčki,« je priznal, »ampak midva s Pikijem.« Sledil je izčrpen pogovor nočnem in dnevnem vrtnarstvu, o bedenju in spanju in še o marsičem drugem.
> 169	117	535	514	potrjuje	oseba: učitelj -[potrjuje]-> žival: tigri	Učitelj je pokimal in rekel: »Nikar ne skrbi, vse bo v redu.« »Imaš klovne?« sem vprašal. Učitelj je pokimal. »Pa tigre?« Učitelj je spet pokimal. »Pa žonglerje?« »Žongler boš ti,« je rekel učitelj. »Jaz?« »Seveda, saj na počitnicah zmeraj žongliraš z balinčki.« »Kot veš, samo s tremi kroglami.« »Za moj cirkus to zadostuje,« je rekel direktor. »Tu imaš krogle.
> 170	121	150	677	se namuči	oseba: govorec -[se namuči]-> dogodek: žonglerska točka	Pošteno sem se namučil, preden sem svoje tri krogle dvajsetkrat zavrtel, ne da bi mi katera padla na tla. Zato pa mi je potem, ko sem se priklanjal občinstvu, padla ena iz žepa na kurje oko. Na vrsti je bila zadnja in glavna točka spored: dresura tigrov. Direktor je povedal, da so en lev in dva tigra pobegnili, ampak da to nič ne de, ker preostali tiger zaleže za štiri.
> 171	122	513	200	prinaša	žival: tiger -[prinaša]-> predmet: krogla	Prosil je za popolno tišino, ker je zver zelo živčna in bi lahko pobegnila, gledalcem pa bi tako ušla najboljša točka sporeda. Občinstvo je zadržalo dih. Na direktorjev znak je Piki splezal na postelje in vzdignil velik obroč. Direktor je zvil iz papirja kroglo, jo dal povohati tigru, potem pa jo vrgel skoz obroč čez obe postelji. Tiger se je v elegantnem skoku pognal skoz obroč, preletel postelji in pristal na drugi strani na tleh. Pograbil je kroglo in jo prinesel direktorju.
> 172	126	415	671	vadi	skupina: pripravniki -[vadi]-> vaja: žabje skoke	Na njej so pripravniki v travi za blokom vadili žabje skoke, počepe in prevale. Čez teden dni so prešli na vajo »polet«. Oblečeni v padalske »telovnike« so na terasi ure in ure bingljali na vrveh za sušenje perila. Na koncu je sledil še preskus vrtoglavice. Polkovnik je bodoče padalce posadil v centrifugo in jih tako prevrtel, da so prišli ven čisto ploščati. S to vajo se je tečaj končal in za naslednji dan so bili napovedani skoki. Polkovnik me je povabil na prireditev.
> 173	129	12	152	obvisi	oseba: Filip -[obvisi]-> predmet: grm forsicije	Po krajšem premisleku je odskočišče prestavil na konec terase in Piki je dobil dovoljenje za skok. Skočil je strmo, pritegnil vrvi, srečno prijadral mimo balkonov in z lepim prevalom pristal v travi za blokom. Zadnji je skočil Filip. Tudi on se je izognil balkonom, vendar je tik pred pristankom obvisel na grmu forsicije. »Kaj praviš?« je vprašal učitelj. »Za prvič odlično,« sem rekel. »Fantje so pogumni, a ne poznajo še vetra.«
> 174	130	535	414	govori	oseba: učitelj -[govori]-> oseba: pripovedovalec	»Ja, veter,« je rekel učitelj malce potlačeno. Pomignil je z glavo proti balkonom. »Treba bo iti po Marka in Jupitra. Greš z mano?« »S tabo?« sem se začudil. »No, vsaj po Marka,« je silil učitelj. »Ti ga drugače ne bodo dali?« Učitelj je skomignil z rameni. »Naj bo,« sem rekel, »pojdiva.« Pozvonila sva v drugem nadstropju. Odprla nama je stara gospa.
> 175	130	535	414	prosi	oseba: učitelj -[prosi]-> oseba: pripovedovalec	»Ja, veter,« je rekel učitelj malce potlačeno. Pomignil je z glavo proti balkonom. »Treba bo iti po Marka in Jupitra. Greš z mano?« »S tabo?« sem se začudil. »No, vsaj po Marka,« je silil učitelj. »Ti ga drugače ne bodo dali?« Učitelj je skomignil z rameni. »Naj bo,« sem rekel, »pojdiva.« Pozvonila sva v drugem nadstropju. Odprla nama je stara gospa.
> 176	132	414	147	se zahvali	oseba: pripovedovalec -[se zahvali]-> oseba: gospa	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 177	132	414	48	pobere	oseba: pripovedovalec -[pobere]-> oseba: Piki	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 178	133	61	335	odlikoval	oseba: Polkovnik -[odlikoval]-> oseba: padalci	Opozoril sem ga, da bo tokrat sam pobiral padalce po tujih balkonih. To mu ni bilo všeč in zato je tekmovanje prestavil. Kljub temu smo se zbrali naslednjega dne spet na terasi. Polkovnik je padalce odlikoval z odlikovanji PP. To ne pomeni, da so tudi oni postali padalski polkovniki, temveč, da so dobili častni naslov POGUMNI PADALEC. Ko je hotel polkovnik pripeti značko še meni, sem odločno zatrdil, da ne mislim skočiti s terase ne s padalom, ne brez njega.
> 179	133	61	622	hotel	oseba: Polkovnik -[hotel]-> predmet: značko	Opozoril sem ga, da bo tokrat sam pobiral padalce po tujih balkonih. To mu ni bilo všeč in zato je tekmovanje prestavil. Kljub temu smo se zbrali naslednjega dne spet na terasi. Polkovnik je padalce odlikoval z odlikovanji PP. To ne pomeni, da so tudi oni postali padalski polkovniki, temveč, da so dobili častni naslov POGUMNI PADALEC. Ko je hotel polkovnik pripeti značko še meni, sem odločno zatrdil, da ne mislim skočiti s terase ne s padalom, ne brez njega.
> 180	134	76	404	zbiral	oseba: Učitelj -[zbiral]-> značilnost: predloge	Polkovnik mi je pojasnil, da pomeni PP prav tako POBIRALEC PADALCEV. Ta naslov sem spreje, nakar smo vsi zadovoljni odšli na PP ali popoldanski počitek. Praznik Medvedja šola dolgo ni imela svojega praznika. Učitelj je zbiral predloge in tehtal dneve, vendar je v vsakem našel kakšno napako. Eden je bil preblizu novega leta, drugi preblizu počitnic, tretjega so praznovali že kje drugje. Ko je že skoraj obupal, je prišel k njemu Piki in rekel: »Zdi se mi, da imam dober predlog.«
> 181	2	48	243	vozi	oseba: Piki -[vozi]-> predmet: medvedja kočija	Jaz sem učiteljev oče in zato dobro poznam Pikija in učitelja. Včasih se skupaj igramo človek ne jezi se. S Pikijem se dobro razumeva, z učiteljem pa imam včasih težave. Piki zmeraj pametno molči, učitelj pa mi včasih ugovarja. Nič ne pomaga, če mu rečem, da sem jaz ravnatelj. Pikiju ni nikoli dolgčas. Vsako jutro se z medvedjo kočijo, v kateri je nekoč učiteljeva starjša sestra prevažala punčke, odpelje v medvedjo šolo.
> 182	4	48	535	pripoveduje	oseba: Piki -[pripoveduje]-> oseba: učitelj	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.
> 183	4	48	535	poboža	oseba: Piki -[poboža]-> oseba: učitelj	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.
> 184	5	535	164	je nezaupljiv	oseba: učitelj -[je nezaupljiv]-> značilnost: imenitne jedi	V sanjah se včasih pogovarjava po francosko. Pravi, da je bil nekoč v Parizu in da tam medvede kličejo Žužu. Prav rad mu verjamem, vendar se strinjava, da je Piki lepše ime. Mogoče me bo Piki naučil medvedjega jezika. O tem se še nisva pogovarjala, ker sva oba zelo zaposlena. Piki se mora učiti za šolo, jaz pa moram pisati knjige. Francoska solata Imeli smo goste in učiteljeva mama je pripravljala razne imenitne jedi. Takih jedi ne jemo vsak dan in zato je učitelj do njih nezaupljiv.
> 185	6	221	146	dodaja	oseba: mama -[dodaja]-> značilnost: gorčica	Kot pravi kuhelmuc se je sukal po kuhinji in opazoval mamo, ki je rezala kumarice, krompir, korenček, zeleno in kolerabo. Vse te stvari jemo po navadi vsako posebej in nekatere od njih je tudi učitelj. A mama jih je pomešala ter jim dodala še gorčico in majonezo, tako da je nastala čudna godlja, ki ji pravimo francoska solata. Učitelj je strmel v čudo in mama je rekla: »Boš malo pokusil?« Učitelj je odločno odkimal: »Ne, hvala, ne bom.«
> 186	9	221	48	nudi	oseba: mama -[nudi]-> oseba: Piki	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 187	10	221	535	vpraša	oseba: mama -[vpraša]-> oseba: učitelj	Tako je pojedel še drugo, tretjo in četrto žlico, potem pa se je lepo obliznil in se priklonil, kar je pomenilo: hvala. »Si videl?« je rekla mama učitelju. »Pha,« je rekel učitelj, »jasno, Piki je Francoz, Parižan. Tam vsi Žužuji jejo francosko solato, saj mi je pravil. Jaz pa nisem Žužu, ampak medvedji učitelj. Si že slišala, da bi kdaj kak medvedji učitelj jedel francosko solato?«
> 188	12	535	73	pogovarja se	oseba: učitelj -[pogovarja se]-> oseba: Timika	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 189	13	48	226	opazuje	oseba: Piki -[opazuje]-> žival: maček	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 190	13	226	678	izdaja zvok	žival: maček -[izdaja zvok]-> značilnost: žvižganje	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 191	13	535	659	opozarja	oseba: učitelj -[opozarja]-> prostor: šola	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 192	14	48	226	vidi	oseba: Piki -[vidi]-> žival: maček	Ozrl sem se skozi okno, pa sem zagledal mačka.« »To se ti je sanjalo,« je rekel učitelj. »Našega mačka poznam. Marsikaj zna, žvižga pa zagotovo ne.« Piki je skomignil z rameni: »Jaz nisem kriv, če je včeraj žvižgal.« »Sedi,« je strogo rekel učitelj. »Dovolj je šale. Če jaz rečem, da mačke ne žvižgajo, potem ne žvižgajo, razumeš?« »Razumem, da ne žvižgajo,« je rekel Piki in sedel.
> 193	15	285	535	vpraša	oseba: moški -[vpraša]-> oseba: učitelj	»Nadaljujmo,« je rekel učitelj. »Marko, povej …« Tedaj je pozvonilo. Učitelj je prenehal sredi stavka. Potrkal je s svinčnikom po mizi in rekel: »Takoj se vrnem. Med tem ponavljajte.« Medvedje so se zagledali v zvezke, učitelj pa je odšel v vežo. Previdno, komaj za dlan široko je odprl vrata in pokukal ven. Zunaj je stal moški iz sosednega stopnišča. »Je očka doma?« je vprašal. Učitelj je odkimal. »Pa mama?«
> 194	21	535	48	ima prednost	oseba: učitelj -[ima prednost]-> oseba: Piki	Učitelj ni nič opazil in tako sta igrala naprej. Začela sta ne veliko zamenjevati ﬁgure in Piki je vsako, ki jo je pobral z deske, najprej malo pogledal z leve in desne, potem pa jo je požrl. Polagoma sta se bližala koncu igre. Kljub temu, da je Piki na veliko jedel učiteljeve ﬁgure, je bil učitelj spretnejši in tako je Pikiju kmalu ostal samo še kralj s trdnjavama, učitelj pa je imel ob kralju in trdnjavah še kraljico.
> 195	22	535	48	zmaguje	oseba: učitelj -[zmaguje]-> oseba: Piki	»Zdaj te bom pa matiral,« je rekel učitelj in napovedal šah. Pikijev črni kralj je begal sem in tja po deski in zašel na nevarni rob. Za silo ga je še branila ena izmed trdnjav, in ko je Piki prišel na potezo, se je spet globoko zamislil. »Kaj pa spet mečkaš,« je rekel učitelj. »Saj ti tako nič ne pomaga, matiral te bom in to takoj.« Tedaj se je Piki odločil.
> 196	23	48	401	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: prebrisan	S trdnjavo je napadel belega kralja, in medtem ko se je učitelj umikal, je smuknil z deske svojega kralja in ga v trenutku požrl. Pri tem je kazal čisto nedolžen obraz. Učitelj se je pripodil s kraljico, podrl Pikijevo trdnjavo in rekel: »Mat.« »Ni mat,« je rekel Piki. »Kako da ne?« je rekel učitelj. Potem je opazil, da črnega kralja ni na šahovnici. »Kje pa imaš kralja? Saj je ravnokar stal tukaj.
> 197	25	535	465	razume	oseba: učitelj -[razume]-> značilnost: situcija	« Šele zdaj je učitelj razumel za kaj gre. Belih ﬁgur, ki jih je Piki pobral, ni bilo nikjer. »Zakaj si jih pa požrl?« je vprašal učitelj. »Saj si mi vendar sam rekel, naj požrem kmeta, potem pa sem požrl še druge,« je rekel Piki. »Kaj bova pa zdaj?« je rekel učitelj. »Kako pa naj zdaj šahirava?« Piki je rekel: »Prosi očka, naj ti kupi nov šah.
> 198	25	48	95	požre	oseba: Piki -[požre]-> figurka: bele figure	« Šele zdaj je učitelj razumel za kaj gre. Belih ﬁgur, ki jih je Piki pobral, ni bilo nikjer. »Zakaj si jih pa požrl?« je vprašal učitelj. »Saj si mi vendar sam rekel, naj požrem kmeta, potem pa sem požrl še druge,« je rekel Piki. »Kaj bova pa zdaj?« je rekel učitelj. »Kako pa naj zdaj šahirava?« Piki je rekel: »Prosi očka, naj ti kupi nov šah.
> 199	25	535	465	izrazi zaskrbljenost	oseba: učitelj -[izrazi zaskrbljenost]-> značilnost: situcija	« Šele zdaj je učitelj razumel za kaj gre. Belih ﬁgur, ki jih je Piki pobral, ni bilo nikjer. »Zakaj si jih pa požrl?« je vprašal učitelj. »Saj si mi vendar sam rekel, naj požrem kmeta, potem pa sem požrl še druge,« je rekel Piki. »Kaj bova pa zdaj?« je rekel učitelj. »Kako pa naj zdaj šahirava?« Piki je rekel: »Prosi očka, naj ti kupi nov šah.
> 200	28	48	212	primerja	oseba: Piki -[primerja]-> žival: lev	»Ko sem bil jaz na vrsti, nas je bilo pač trideset. Je že bil tak mesec. Prav dobro vem, da nas je bilo trideset, ker je mene naredila prvega in sem imel čas šteti. Imela je krojne pole za velike in srednje in majhne medvedke. Zame je izbrala posebno lep kroj. Razen tega mi je prišila rjav in bel pliš. Takega kožuha nima vsak medvedek. Po večini so rumeni, kot da bi bili levi in ne medvedi. Si že kdaj videl rjavega leva?«
> 201	83	416	310	se začne	dogodek: prireditev -[se začne]-> čas: ob treh	Medvedje prejšnji večer od veselja sploh niso mogli zaspati, Boksali in ščipali so se pod odejo, tako da sta Floki in Benjamin celo padla iz postelje. Učitelj je bil na dan otvoritve zelo zaposlen, medvedje pa so se lišpali in krtačili, kot da bi šli na gostijo. Mnogi so si kupili kariraste čepice, Timika pa je dišala, kot bi padla v steklenico s parfumom. Ob treh se je prireditev končno začela. Lepo okrašeni prostore v dnevni sobi je bil razdeljen na sejmišče in zabavišče.
> 202	83	422	120	je okrašen	prostor: prostor -[je okrašen]-> prostor: dnevna soba	Medvedje prejšnji večer od veselja sploh niso mogli zaspati, Boksali in ščipali so se pod odejo, tako da sta Floki in Benjamin celo padla iz postelje. Učitelj je bil na dan otvoritve zelo zaposlen, medvedje pa so se lišpali in krtačili, kot da bi šli na gostijo. Mnogi so si kupili kariraste čepice, Timika pa je dišala, kot bi padla v steklenico s parfumom. Ob treh se je prireditev končno začela. Lepo okrašeni prostore v dnevni sobi je bil razdeljen na sejmišče in zabavišče.
> 203	85	19	347	obiskuje	oseba: Jupiter -[obiskuje]-> prostor: paviljon z ogledali	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 204	85	48	19	vpraša	oseba: Piki -[vpraša]-> oseba: Jupiter	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 205	86	19	48	govori	oseba: Jupiter -[govori]-> oseba: Piki	»Pa dajva,« je rekel Jupiter. Sedla sta v majhen vlakec in se po krajši vožnji ob ribniku zapeljala v mračen predor. V trdi temi se je čulo samo bobnenje koles. Na lepem pa se je strašno zabliskalo in zagrmelo, vlak se je stresel, kot da bo vsak hip iztiril, čez hip pa je spet bila popolna tema. Grmenje in bliskanje se je ponovilo še dvakrat, potem pa je vlak zavozil skoz vrata z žarečim napisom DVORANA SMRTI.
> 206	86	48	561	sedlo	oseba: Piki -[sedlo]-> predmet: vlakec	»Pa dajva,« je rekel Jupiter. Sedla sta v majhen vlakec in se po krajši vožnji ob ribniku zapeljala v mračen predor. V trdi temi se je čulo samo bobnenje koles. Na lepem pa se je strašno zabliskalo in zagrmelo, vlak se je stresel, kot da bo vsak hip iztiril, čez hip pa je spet bila popolna tema. Grmenje in bliskanje se je ponovilo še dvakrat, potem pa je vlak zavozil skoz vrata z žarečim napisom DVORANA SMRTI.
> 207	86	561	10	zavozil	predmet: vlakec -[zavozil]-> prostor: Dvorana smrti	»Pa dajva,« je rekel Jupiter. Sedla sta v majhen vlakec in se po krajši vožnji ob ribniku zapeljala v mračen predor. V trdi temi se je čulo samo bobnenje koles. Na lepem pa se je strašno zabliskalo in zagrmelo, vlak se je stresel, kot da bo vsak hip iztiril, čez hip pa je spet bila popolna tema. Grmenje in bliskanje se je ponovilo še dvakrat, potem pa je vlak zavozil skoz vrata z žarečim napisom DVORANA SMRTI.
> 208	87	19	302	čuti	oseba: Jupiter -[čuti]-> predmet: nekaj	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 209	87	48	304	gre	oseba: Piki -[gre]-> prostor: nevarni predor	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 210	87	19	304	gre	oseba: Jupiter -[gre]-> prostor: nevarni predor	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 211	88	48	19	govori	oseba: Piki -[govori]-> oseba: Jupiter	»Ko te poboža,« je rekel Piki, »zgrabi z vso močjo. »Zanesi se name,« je zamrmral Jupiter. Spet sta se peljala skoz grmenje in bliskanje in napeto čakala na pravi trenutek. V Dvorani smrti sta potem zagrabila. V tem hipu se je Hiša strahov prislužila svoje ime. Smrt je strašno zarjula, se iztrgala Pikiju in Jupitru iz rok ter se skoz streho pognala iz hiše.
> 212	89	18	535	se pogovarja	oseba: Josip Jupiter -[se pogovarja]-> oseba: učitelj	Žal je v temi slabo preračunala smer in padla naravnost v stari lavor, ki ga je učitelj spremenil v ribnik. Nastala je strašna povodenj, smrt pa je iz lavorja v podobi mokrega mačka jadrno švignila na balkon. Piki in Josip Jupiter sta se imenitno zabavala. Vsakemu, ki ju je hotel poslušati, sta pripovedovala, da sta držala smrt že za rep in je le malo manjkalo, pa bi jo stlačila v vrečo. Zatrjevala sta, da tako sijajnega novoletnega sejma še ni bilo. Manj navdušenja pa je kazal učitelj.
> 213	90	2	535	odgovarja	oseba: Benjamin -[odgovarja]-> oseba: učitelj	Bil je strašno jezen na smrt, ki je padla v ribnik, zaradi česar je moral tri ure drgniti parket v dnevni sobi. Spominske knjige Na lepem so vsi medvedje imeli spominske knjige. Pri pouku je kar naprej nekaj šumelo in krožilo pod klopmi. Ko je učitelj pri računstvu vprašal Benjamina: »Koliko je ena in ena?« je ta odgovoril: »Ena in ena je dve-nikar ne pozabi na me!« »Ne bom,« je rekel učitelj in mu zapisal velik minus v vedenju.
> 214	92	482	73	pripada	predmet: spominska knjiga -[pripada]-> oseba: Timika	Učitelju so bili verzi všeč, dvakrat jih je prebral in malo je manjkalo, pa bi Pikija pohvalil. Vendar se je še pravi čas spomnil, da je učence kaznoval, in tako je z resnim obrazom segel po drugi spominski knjigi. Bila je vezana v rdeče usnje in na platnicah je pisalo Timika. Knjiga je bila skoraj polna, nekateri medvedje so se vpisali celo po večkrat. Na začetku je bila okorno narisana ladjica, zraven pa verzi: Nisem pesnik ne risar, kaj ti naj poklonim v dar?
> 215	93	187	399	vsebuje	predmet: knjiga -[vsebuje]-> vsebina: pravljične hišice	Za spomin narišem barko se podpišem stari Marko. Učitelj je požrl slino in listal naprej. Knjiga je bila polna nageljnov, vrtnic in pravljičnih hišic. Pod eno izmed njih je pisalo: Tukaj hišica stoji, v hiši deklica živi, ko na okno se nasloni, se ji Benjamin prikloni. na naslednji strani je bila v tiskanih črkah ovekovečena modrost Marka Prvega: Timika,mladost je vsaka kakor mehka, gosta dlaka, a medvedu kakor muli kožuh kmalu se oguli. »Kaj takega,« je pomislil učitelj.
> 216	94	12	554	piše	oseba: Filip -[piše]-> vsebina: verze	Sledilo je nekaj praznih listov, potem pa sta bili čez celo stran narisani dve Timiki, ena objokana in ena nasmejana. Spodaj je stalo kratko in jedrnato: Bodi v sreči, bodi v sili zmeraj nate misli Filip. Medvedje so že desetič pisali »Med poukom mora biti spominska knjiga v torbi«, učitelj pa je začel prebirati Pikijevo knjižico. Pod veliko srebrno raketo je našel verze: Lunibus leti na Luno Piki je njegov šofer. Potnike ima na skrbi zvesti Josip Jupiter.
> 217	94	249	494	piše	skupina: medvedje -[piše]-> vsebina: stavek	Sledilo je nekaj praznih listov, potem pa sta bili čez celo stran narisani dve Timiki, ena objokana in ena nasmejana. Spodaj je stalo kratko in jedrnato: Bodi v sreči, bodi v sili zmeraj nate misli Filip. Medvedje so že desetič pisali »Med poukom mora biti spominska knjiga v torbi«, učitelj pa je začel prebirati Pikijevo knjižico. Pod veliko srebrno raketo je našel verze: Lunibus leti na Luno Piki je njegov šofer. Potnike ima na skrbi zvesti Josip Jupiter.
> 218	95	249	73	pridružujejo	skupina: medvedje -[pridružujejo]-> oseba: Timika	»Upam, da ne bosta tudi tam uvedla postajališč,« je zase rekel učitelj. Medtem je zazvonilo. Medvedje so pospravili stvari in učitelj je moral prenehati z branjem spominskih knjig. Ozrl se je po razredu in vprašal: »Ste napisali?« »Smo,« so odgovorili medvedje v zboru. Potem se je vzdignila Timika in rekla: »Tovariš učitelj, lepo prosim, če bi mi kaj napisali v spominsko!« »Meni tudi, meni tudi,« so se oglasili še drugi medvedje.
> 219	96	535	512	izjavi	oseba: učitelj -[izjavi]-> značilnost: težava	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 220	97	535	249	obljubljajo	oseba: učitelj -[obljubljajo]-> skupina: medvedje	Bojim se, da bodo morali učitelj in medvedje še malo počakati. Gasilska četa Pozimi sva z učiteljem kurila peči. »Pri kurjavi moraš biti previden,« sem rekel, »kajti če skoči ogenj iz peči, lahko zgorita parket in pohištvo, nazadnje pa še hiša.« Učitelj je prikimal in rekel: »Opozoriti bom moral tudi medvede.« Ko sem tistega dne po kosilu malo zadremal, se je iz kuhinje kar na lepem oglasilo živahno trobentanje.
> 221	100	48	559	je	oseba: Piki -[je]-> poklic: višji gasilec	Bili so zelo požrtvovalni in zato sem jih po končani vaji s poveljnikom vred povabil na malinovec. Poslej je trobenta vsak dan po kosilu klicala gasilce »na pomoč«. Četa je kmalu obvlada tudi motorizacij in zvokom trobente so se pridružili zvoki gasilske sirene in cviljenje gum gasilskega avta, ki ga je višji gasilec Piki vozil na »kraj požara«.
> 222	101	287	317	je	skupina: moštvo -[je]-> značilnost: odlično izurjeno	Poveljnik je rekel, da bi četi zelo koristile »vroče vaje«, to se pravi, gašenje »požara« v peči dnevne sobe, vendar mu tega kot višji gasilski inšpektor nisem mogel dovoliti. Približala se je pomlad. Nehali smo kuriti peči in nevarnost požarov se je zmanjšala skoraj na ničlo. A poveljnik je menil, da je treba znanje preizkusiti, in tako je četa v kopalnici priredila gasilski miting pod nazivom POŽAR V NBOTIČNIKU. Prepričal sem se, da je moštvo odlično izurjeno.
> 223	103	109	2	zadeva	značilnost: curek -[zadeva]-> oseba: Benjamin	Metala sta jih v globino, kjer so jih štirje gasilci spretno lovili v ponjavo, Medtem je višji gasilec Piki pripravil motorno brizgalno. Na vodovodno pipo je nataknil dolgo cev ter z roba umivalnika usmeril močan curek proti »plamenom«. Žal mu je na mokrih tleh spodrsnil in je padel, vendar pa cevi tudi med padcem ni izpustil iz rok. Po nesreči je curek zadel reševalca Benjamina in Filipa, ki sta iz vrtoglave višine strmoglavila na ponjavo, s katere se je samo trenutek prej pobral Piki.
> 224	104	48	527	zatrobenta	oseba: Piki -[zatrobenta]-> predmet: trobenta	S cevjo, iz katere je še zmeraj bruhala voda, je »pogasil« tudi nekaj na tleh stoječih gasilcev. Zdaj so si vsi otepali mokre kožuhe in nič kaj prijazno gledali Pikija. Ker rokoborba ni bila na sporedu gasilskega mitinga, je poveljnik brž izključil motorno brizgalno ter razglasil, da je požar pogašen in stanovalci rešeni. Gasilci so pospravili svojo opremo, Piki je zatrobental in odpeljali so se domov. Na kratki slovesnosti pred gasilskim domom je učitelj povedal, da so danes doživeli ognjeni krst in postali pravi gasilci.
> 225	106	221	584	gre	oseba: mama -[gre]-> prostor: vrtnarija	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 226	31	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 227	34	48	669	se spominja	oseba: Piki -[se spominja]-> oseba: Žužu številka 2	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 228	34	48	668	ima vzdevek	oseba: Piki -[ima vzdevek]-> značilnost: Žužu številka 1	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 229	35	50	305	piše	oseba: Piki Jakob -[piše]-> oseba: neznani prejemnik	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 230	37	667	50	pošlje pismo	oseba: Žužu -[pošlje pismo]-> oseba: Piki Jakob	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 231	39	48	626	obiskuje	oseba: Piki -[obiskuje]-> oseba: zobozdravnik	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 232	40	626	48	je prijatelj	oseba: zobozdravnik -[je prijatelj]-> oseba: Piki	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 233	42	102	611	pobira	oseba: bolniška sestra -[pobira]-> dokument: zdravstvena knjižica	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 234	43	48	610	odgovarja	oseba: Piki -[odgovarja]-> oseba: zdravnik	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 235	44	48	610	grize	oseba: Piki -[grize]-> oseba: zdravnik	»Tukaj je torej nepridiprav,« je rekel zdravnik in potipal še s prstom, da bi videl, če se že maje. Pikiju se je zdelo, da vidi vse zvezde in v hipu je zaprl gobec. Zdaj je zdravnik zavpil »au« in izvlekel boleči prst. »Piki,« je rekel strogo, »sva se tako zmenila? Jaz ti hočem pomagati, ti me pa grizeš. Ali je to pošteno?« Piki je odkimal.
> 236	49	251	98	tekajo	oseba: medvedji -[tekajo]-> prostor: berezov gaj	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 237	49	251	125	podrli	oseba: medvedji -[podrli]-> predmet: drevesa	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 238	49	251	191	imajo težave	oseba: medvedji -[imajo težave]-> prostor: kopalnica	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 239	49	12	93	pade	oseba: Filip -[pade]-> predmet: banjo	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 240	51	48	162	spozna	oseba: Piki -[spozna]-> žival: hudi tiger	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 241	52	162	48	drvi	žival: hudi tiger -[drvi]-> oseba: Piki	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 242	55	48	70	vzklika	oseba: Piki -[vzklika]-> oseba: Stari Marko	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 243	56	48	497	dostopa	oseba: Piki -[dostopa]-> prostor: stenska lekarnica	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 244	58	48	81	zaužije	oseba: Piki -[zaužije]-> zdravilo: aspirin	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 245	58	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 246	59	535	48	pojasnjuje	oseba: učitelj -[pojasnjuje]-> oseba: Piki	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 247	61	48	640	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: čiste petke	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 248	62	48	392	gre na	oseba: Piki -[gre na]-> dogodek: počitnice	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 249	63	535	150	vpraša	oseba: učitelj -[vpraša]-> oseba: govorec	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 250	64	48	455	vzame	oseba: Piki -[vzame]-> obutev: sandale	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 251	65	535	83	vozi	oseba: učitelj -[vozi]-> vozilo: avto	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 252	65	48	569	pozdravlja	oseba: Piki -[pozdravlja]-> skupina: vozniki	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 253	69	535	150	postavil	oseba: učitelj -[postavil]-> oseba: govorec	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 254	70	48	605	prižgal	oseba: Piki -[prižgal]-> značilnost: zasenčene luči	Zdaj sva se lahko podala na prometne ulice in prevozila sva vse po vrsti od štiripasovnice na hodniku do enosmernih v učiteljevem kabinetu. Nekega dne sva se peljala skozi veliki predor pod posteljami in Piki je prižgal zasenčene luči. Na drugi strani predora so se tedaj prikazali žarometi velikega tovornjaka. Imel je prižgane dolge luči, ki so naju zelo slepile. »Pobliskaj mu,« sem rekel Pikiju. Piki je pobliskal, ampak tovornjak ni skrajšal luči. Piki se je razjezil. »Čakaj, falot,« je zapihal.
> 255	71	48	519	ugotovil	oseba: Piki -[ugotovil]-> predmet: tovornjak	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 256	72	150	48	vprašal	oseba: govorec -[vprašal]-> oseba: Piki	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 257	74	48	84	vozi	oseba: Piki -[vozi]-> predmet: avtobus	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 258	76	48	18	odgovoril	oseba: Piki -[odgovoril]-> oseba: Josip Jupiter	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 259	76	48	381	predlagal	oseba: Piki -[predlagal]-> značilnost: postajališča	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 260	76	386	608	vstopali	oseba: potniki -[vstopali]-> prostor: začetna postaja	»Vsi vstopajo na začetku,« je rekel Josip Jupiter, »izstopajo pa na koncu. Ni to malo preveč enolično?« »Prav imaš,« je rekel Piki. »Uvedla boa postajališča.« Že naslednji dan so tri nove table označevale postajališča STARI GOJZAR, PODPEČ in MAČJA SKLEDA. Avtobus je odslej ustavil štirikrat, kar se je zdelo vozniku in sprevodniku imenitno. Potniki pa niso pokazali zanimanja in so še zmeraj vstopali na začetni, izstopali pa na končni postaji.
> 261	79	18	487	predstavi	oseba: Josip Jupiter -[predstavi]-> delo: sprevodnik	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 262	81	488	247	se prikaže	oseba: sprevodnik -[se prikaže]-> oseba: medvedje	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 263	81	247	116	tolče	oseba: medvedje -[tolče]-> predmet: dežniki	Iz njega so se začeli pobirati medvedje in ko se je prikazal sprevodnik, so spet planili po njem. Piki ni zapustil tovariša v sili in se je pogumno pognal v bojni metež. Tolkli so se s torbicami in dežniki ter niso prizanašali ne sebi ne avtobusu. K sreči se je na prizorišču bitke pravočasno prikazal višji policijski inšpektor v podobi učitelja. Polovil je pretepače in jih odpeljal na postajo milic. Tam jih je pošteno izprašal, potem pa krivcem naložil hude, a pravične kazni.
> 264	82	48	150	obiskuje	oseba: Piki -[obiskuje]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 265	82	69	150	obiskuje	oseba: Sprevodnik -[obiskuje]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 266	82	48	150	obljublja	oseba: Piki -[obljublja]-> oseba: govorec	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.
> 267	135	76	434	zahteval	oseba: Učitelj -[zahteval]-> značilnost: razlago	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 268	135	48	607	ponudil	oseba: Piki -[ponudil]-> značilnost: začetek pomladi	»Razloži ga, prosim, kratko in jedrnato,« je rekel učitelj. »Začetek pomladi,« je rekel Piki. »Ni slabo. Zakaj?« »Zaradi prebujanja gozdnih medvedov iz zimskega spanja.« »Dobro. Predlagaš tudi ime?« »Velika Medvednica.« »Odlično,« je rekel učitelj. »Piki, ti si nadmedved!« Predlog je bil sprejet in začele so se priprave za praznovanje. Učitelj je sestavil spored ter določil pevce, igralce, plesalce in recitatorje.
> 269	137	48	234	zatrobil	oseba: Piki -[zatrobil]-> predmet: medeninast rog	Učenci so šolo okrasili s kitami pomladanskega cvetja in ob napovedani uri skupaj z učiteljem in gosti zasedli prostore v veliki šolski dvorani. Zavesa se vzdignila in na odru je stal Piki. Prislonil je h gobcu medeninast rog in trikrat zateglo zatrobil. Začula sta se šum in štorkljanje in od vseh strani so začeli hiteti medvedje. Pretegovali so se in zehali, kakor da bi se pravkar zbudili iz zimskega spanja. Bili so člani medvedjega pevskega zbora.
> 270	138	356	353	peli	skupina: pevci -[peli]-> značilnost: pesmijo	Zbrali so se na odru in začeli spored s pesmijo »Kadar medved se zbudi , iz brloga prihiti«, ki jo je za današnjo proslavo zložil medvedji učitelj. Piki je pevce dobro izuril, peli so tiše in bolj pravilno kakor pred tedni. Občinstvo je vneto ploskalo njim in skladatelju. Po kratkem učiteljevem govoru je nastopil Trio Marko s plesom Marko skače.
> 271	139	241	505	igrali	skupina: medvedi -[igrali]-> predmet: tamburice	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 272	139	73	63	nastopila	oseba: Timika -[nastopila]-> značilnost: Pomlad	Nekaj medvedov je igralo na tamburice trije Marki (Prvi, Drugi in Stari) pa so plesali s takšnim navdušenjem, da se je oder pod njimi kar upogibal, in je bilo čudno, da deske niso popokale. Na burne zahteve gledalcev so morali točko ponoviti. Sledil je kratek prizor, v katerem je nastopila Timika kot Pomlad in Benjamin kot medved Domberdan.
> 273	141	241	220	prejeli	skupina: medvedi -[prejeli]-> predmet: makismed	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 274	142	535	387	predlagal	oseba: učitelj -[predlagal]-> značilnost: potovanje	« sem vprašal začuden. »V Pariz,« je ponovil učitelj. »Piki bi rad obiskal Žužuja.« »Razumem,« sem rekel. »Kako bi pa šli?« »Ti bi nas peljal z avtom.« »Ali ni do Pariza preblizu?« sem rekel. »Kaj ko bi šli še kam, ko bomo ravno na poti?« »Seveda,« je takoj poprijel učitelj. »S Pikijem sva ti hotela predlagati, da bi iz Pariza odpotovali na severni tečaj.«
> 275	143	535	345	predlagal	oseba: učitelj -[predlagal]-> predmet: pasja vprega	»Na severni tečaj?« »Ja, Piki bi rad videl severne medvede.« »Česa ne poveš? Severne medved?« »Ja, pa pingvine in mrože in kar je še ram zgoraj.« »Kako pa misliš priti tja gor?« sem vprašal. »Ti bi nas peljal z avtom.« »Na severni tečaj, kaj?« »Ne čisto do tja. Do Eskimov. Pri njih bi najeli pasjo vprego.« »Aha,« sem rekel.
> 276	144	48	618	ima željo	oseba: Piki -[ima željo]-> mitološka bitja: zmaji	»Ampak, če Pikija vsaj malo poznam, mu severni medvedi ne bodo zadostovali.« »Seveda ne,« je vneto pritrdil učitelj. »Gotovo bi rad videl še leve in tigre in slone in antilope in žirafe in krokodile in kar je še tega tam spodaj.« »Seveda, to bi bilo imenitno.« »Mogoče pa tudi zmaje?« »Ne šali se,« je rekel učitelj. »Jaz govorim resno. Kje so pa zmaji?« »V pravljici.«
> 277	145	535	398	govori	oseba: učitelj -[govori]-> literarna vrsta: pravljica	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 278	146	150	535	vozi	oseba: govorec -[vozi]-> oseba: učitelj	»Jaz sem mislil zares.« »Jaz tudi. Kaj nisi rad v pravljici?« »Ne,« je rekel učitelj. »Raje mi povej, kaj naj rečem Pikiju.« »Povej mu, da gremo v živalski vrt.« »Misliš resno?« »Čisto resno. Danes popoldne.« »Nas boš peljal?« »Seveda.« »nabral bom malo starega kruha.« »Prav.«
> 279	147	150	65	obiskuje	oseba: govorec -[obiskuje]-> prostor: Rožnik	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 280	109	52	598	znosita	skupina: Piki in učitelj -[znosita]-> predmet: zabojčke, lončke, prst in vrečke s čebulicami	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 281	109	48	636	sadita	oseba: Piki -[sadita]-> predmet: čebulice	Potem sta znosila nanjo zabojčke, lončke, prst in vrečke s čebulicami. »Debele moraš saditi globlje,« je rekel učitelj. »Vem,« je pokimal Piki in s taco spretno zajemal zemljo iz vreče. »Mama bo gotovo zelo vesela, ko bo našla vse posajeno.« »Upam, da bo,« je rekel učitelj. Tako sta delala dobro uro. Ko so bile čebulice posajene, sta zemljo zalila, potem sta pospravila časopise in skrbno pometla.
> 282	112	536	446	posadita	oseba: učitelj in Piki -[posadita]-> predmet: rože	Na njih je pisalo: zvonček, rumeni krokus, rumeni tulipan, rožnata hijacinta in tako naprej. »Pri hiši imamo palčke,« je rekla mama, ko se je prikazal učitelj iz spalnice, »poglej, vse rože so posadili.« Učitelj je bil malo v zadregi. »Niso bili palčki,« je priznal, »ampak midva s Pikijem.« Sledil je izčrpen pogovor nočnem in dnevnem vrtnarstvu, o bedenju in spanju in še o marsičem drugem.
> 283	113	585	291	drži se	oseba: vrtnarja -[drži se]-> značilnost: mulasto	Zaradi tega pogovora sta se prevneta vrtnarja tisti dan držala bolj mulasto. Dnevi so tekli in bolj ko se je bližala pomlad, bolj nestrpno smo opazovali zabojčke in lončke, iz katerih so začeli kliti zeleni poganjki. Mene so še posebej zanimali zvončki, toda ko je prišel njihov čas, se niso pokazali v lončku z napisom: zvonček, temveč v zabojčku z napisom: rumeni tulipan.
> 284	115	535	107	vabi	oseba: učitelj -[vabi]-> prostor: cirkus	»Nisem še slišal, da bi se mački ukvarjali z vrtnarstvom,« sem rekel jaz. »O našem se nič ne ve,« je skrivnostno namignil učitelj. »Morda je čarovnik.« Nocoj je polna luna. Za vsak primer sem šel sedet na balkon. Lahko se zgodi, da bo mimo prijezdil naš maček na metli. Cirkus V nedeljo popoldne je deževalo, in da se ne bi preveč dolgočasili, nas je učitelj povabil v cirkus.
> 285	116	108	591	nastopajo	prostor: cirkus bežigrad -[nastopajo]-> predmet: vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba	Na vežna vrata je obesil velik oglas: Cirkus BEŽIGRAD vabi k predstavi ob 16. uri. Nastopajo vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba. Pred nastopom ogled živalskega vrta. Vabljeni! Ogledal sem si vabilo in opozoril učitelja, naj se nikar ne šali z gledalci. »Če jih misliš povleči za os,« sem rekel, »gledalci ne bodo le žvižgali, ampak bodo tudi metali gnila jajca in paradižnike. Ob takih priložnostih je najljubša tarča direktor. Verjetno si to ti?«
> 286	120	117	100	igra	oseba: direktor -[igra]-> predmet: blokflavta	Na začetku je direktor v vlogi cirkuške godbe odigral na blokﬂavto Koračnico palčkov, ki je vsem zelo ugajala in jo je moral ponoviti. Nato je nastopil kot vrvohodec in je z odprtim dežnikom dvakrat prehodil stranice pri posteljah, ne da bi padel na tla. Potem so nas zabavali klovni: Debeli Bongo in Suhi Grintež, Mali Makec in Dolgi Jakec, Nemi Lukec in Lapasti Kljukec. Bili so našemljeni v obleke, ki so se mi zdele znane iz naše omare. Sledila je točka velikega žonglerja Lovikrogle.
> 287	120	6	71	sodeluje	oseba: Debeli Bongo -[sodeluje]-> oseba: Suhi Grintež	Na začetku je direktor v vlogi cirkuške godbe odigral na blokﬂavto Koračnico palčkov, ki je vsem zelo ugajala in jo je moral ponoviti. Nato je nastopil kot vrvohodec in je z odprtim dežnikom dvakrat prehodil stranice pri posteljah, ne da bi padel na tla. Potem so nas zabavali klovni: Debeli Bongo in Suhi Grintež, Mali Makec in Dolgi Jakec, Nemi Lukec in Lapasti Kljukec. Bili so našemljeni v obleke, ki so se mi zdele znane iz naše omare. Sledila je točka velikega žonglerja Lovikrogle.
> 288	120	25	677	izvaja	oseba: Lovikrogla -[izvaja]-> dogodek: žonglerska točka	Na začetku je direktor v vlogi cirkuške godbe odigral na blokﬂavto Koračnico palčkov, ki je vsem zelo ugajala in jo je moral ponoviti. Nato je nastopil kot vrvohodec in je z odprtim dežnikom dvakrat prehodil stranice pri posteljah, ne da bi padel na tla. Potem so nas zabavali klovni: Debeli Bongo in Suhi Grintež, Mali Makec in Dolgi Jakec, Nemi Lukec in Lapasti Kljukec. Bili so našemljeni v obleke, ki so se mi zdele znane iz naše omare. Sledila je točka velikega žonglerja Lovikrogle.
> 289	122	117	513	upravlja	oseba: direktor -[upravlja]-> žival: tiger	Prosil je za popolno tišino, ker je zver zelo živčna in bi lahko pobegnila, gledalcem pa bi tako ušla najboljša točka sporeda. Občinstvo je zadržalo dih. Na direktorjev znak je Piki splezal na postelje in vzdignil velik obroč. Direktor je zvil iz papirja kroglo, jo dal povohati tigru, potem pa jo vrgel skoz obroč čez obe postelji. Tiger se je v elegantnem skoku pognal skoz obroč, preletel postelji in pristal na drugi strani na tleh. Pograbil je kroglo in jo prinesel direktorju.
> 290	125	48	341	ustanovi	oseba: Piki -[ustanovi]-> organizacija: padalsko društvo	Rekel je, da bi padalci tudi pri nas lahko skakali z balkona ali terase in, ker je bil učitelj za to, sta ustanovila padalsko društvo. Medvedje se za novi šport niso preveč zanimali. Razen Pikija so se prijavili samo še Josip Jupiter, Stari Marko in Filip. Mama jim je iz stare rjuhe sešila padala, učitelj, ki je postal padalski polkovnik, pa je sestavil vadbeni urnik. Prva vaja se je imenovala »pristanek«.
> 291	127	338	628	ujema	predmet: padalo -[ujema]-> element: zrak	Pred odskočiščem na južni strani terase so v vrsti stali Marko, Jupter, Piki in Filip v popolni padalski opremi. Po kratkem pregledu je dal polkovnik znak za začetek. Prvi se je s police pognal Stari Marko. Odskok je uspel, padalo je hitro ujelo zrak in se lepo razprostrlo. Nenadni sunek vetra pa je padalca zasukal in ga pognal proti bloku in ga odložil med kaktuse na balkonu drugega nadstropja. »Pozor!« je zaklical poveljnik.
> 292	129	48	521	pristane	oseba: Piki -[pristane]-> prostor: trava za blokom	Po krajšem premisleku je odskočišče prestavil na konec terase in Piki je dobil dovoljenje za skok. Skočil je strmo, pritegnil vrvi, srečno prijadral mimo balkonov in z lepim prevalom pristal v travi za blokom. Zadnji je skočil Filip. Tudi on se je izognil balkonom, vendar je tik pred pristankom obvisel na grmu forsicije. »Kaj praviš?« je vprašal učitelj. »Za prvič odlično,« sem rekel. »Fantje so pogumni, a ne poznajo še vetra.«
> 293	129	414	131	oceni	oseba: pripovedovalec -[oceni]-> skupina: fantje	Po krajšem premisleku je odskočišče prestavil na konec terase in Piki je dobil dovoljenje za skok. Skočil je strmo, pritegnil vrvi, srečno prijadral mimo balkonov in z lepim prevalom pristal v travi za blokom. Zadnji je skočil Filip. Tudi on se je izognil balkonom, vendar je tik pred pristankom obvisel na grmu forsicije. »Kaj praviš?« je vprašal učitelj. »Za prvič odlično,« sem rekel. »Fantje so pogumni, a ne poznajo še vetra.«
> 294	132	147	414	se smeji	oseba: gospa -[se smeji]-> oseba: pripovedovalec	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 295	132	115	414	odpre	oseba: deček -[odpre]-> oseba: pripovedovalec	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 296	132	414	12	pobere	oseba: pripovedovalec -[pobere]-> oseba: Filip	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 297	132	287	123	se vrne	skupina: moštvo -[se vrne]-> prostor: domov	Za vsak primer pa je le šla na balkon in našla tam Starega Marka. Prismejala se je nazaj in midva sva se lepo zahvalila. Z drugimi padalci nisva imela težav. V prvem nadstropju nama je odprl deček, ki se je tudi sam ukvarjal s padalstvom, in je torej vedel, za kaj gre. Potem sva za blokom pobrala še Pikija in Filipa. Moštvo se je vrnilo domov brez izgub. Polkovnik je rekel, da bodo drugi dan spet tekmovali.
> 298	134	61	44	pojasnil	oseba: Polkovnik -[pojasnil]-> značilnost: PP	Polkovnik mi je pojasnil, da pomeni PP prav tako POBIRALEC PADALCEV. Ta naslov sem spreje, nakar smo vsi zadovoljni odšli na PP ali popoldanski počitek. Praznik Medvedja šola dolgo ni imela svojega praznika. Učitelj je zbiral predloge in tehtal dneve, vendar je v vsakem našel kakšno napako. Eden je bil preblizu novega leta, drugi preblizu počitnic, tretjega so praznovali že kje drugje. Ko je že skoraj obupal, je prišel k njemu Piki in rekel: »Zdi se mi, da imam dober predlog.«
> 299	3	18	235	je	oseba: Josip Jupiter -[je]-> oseba: medved	Z njim se peljejo tudi drugi medvedi in vseh skupaj je za cel medvedji avtobus. Dvema ali trem je ime Marko. Eden je Filip in majhni medvedki je ime Timika. Potem so tukaj še Josip Jupiter, Benjamin in Floki, ki sicer ni medved, ampak pes, vendar hodi v medvedjo šolo, ker posebne pasje šole še nimamo. Z učiteljem spiva v isti sobi in zato je Piki včasih tudi leteči medved. Ko se učitelj zjutraj zbudi, pogleda, ali jaz še spim, in mi vrže medveda na glavo.
> 300	4	48	167	je izobražen	oseba: Piki -[je izobražen]-> značilnost: izobražen	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.
> 301	6	221	207	reže	oseba: mama -[reže]-> značilnost: kumarice	Kot pravi kuhelmuc se je sukal po kuhinji in opazoval mamo, ki je rezala kumarice, krompir, korenček, zeleno in kolerabo. Vse te stvari jemo po navadi vsako posebej in nekatere od njih je tudi učitelj. A mama jih je pomešala ter jim dodala še gorčico in majonezo, tako da je nastala čudna godlja, ki ji pravimo francoska solata. Učitelj je strmel v čudo in mama je rekla: »Boš malo pokusil?« Učitelj je odločno odkimal: »Ne, hvala, ne bom.«
> 302	7	221	535	prosi	oseba: mama -[prosi]-> oseba: učitelj	»Samo malo poskusi,« je rekla mama, »samo eno žličko.« Učitelj je odgovoril: »Take čudne jedi mi niso všeč. Ne maram jih.« Mama je vztrajala: »Moraš se navaditi tudi na nove jedi.« Učitelj je bil drugačnega mnenja in je ponovil: »Ne bom.« Mama ni popustila: »Samo eno žličko. Saj ni strup.« Učitelj pa je rekel: »Je. Če to pojem, bom umrl.«
> 303	9	48	645	je	oseba: Piki -[je]-> značilnost: čudež	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 304	9	221	48	vpraša	oseba: mama -[vpraša]-> oseba: Piki	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 305	10	48	134	pojede	oseba: Piki -[pojede]-> jedi: francoska solata	Tako je pojedel še drugo, tretjo in četrto žlico, potem pa se je lepo obliznil in se priklonil, kar je pomenilo: hvala. »Si videl?« je rekla mama učitelju. »Pha,« je rekel učitelj, »jasno, Piki je Francoz, Parižan. Tam vsi Žužuji jejo francosko solato, saj mi je pravil. Jaz pa nisem Žužu, ampak medvedji učitelj. Si že slišala, da bi kdaj kak medvedji učitelj jedel francosko solato?«
> 306	10	535	221	odgovarja	oseba: učitelj -[odgovarja]-> oseba: mama	Tako je pojedel še drugo, tretjo in četrto žlico, potem pa se je lepo obliznil in se priklonil, kar je pomenilo: hvala. »Si videl?« je rekla mama učitelju. »Pha,« je rekel učitelj, »jasno, Piki je Francoz, Parižan. Tam vsi Žužuji jejo francosko solato, saj mi je pravil. Jaz pa nisem Žužu, ampak medvedji učitelj. Si že slišala, da bi kdaj kak medvedji učitelj jedel francosko solato?«
> 307	12	12	535	odgovarja	oseba: Filip -[odgovarja]-> oseba: učitelj	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 308	12	50	231	govori o	oseba: Piki Jakob -[govori o]-> žival: mačke	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 309	12	428	149	izdajajo zvok	žival: ptički -[izdajajo zvok]-> značilnost: gostolij	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 310	13	231	268	izdaja zvok	žival: mačke -[izdaja zvok]-> značilnost: mijavkanje	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 311	13	48	294	delal	oseba: Piki -[delal]-> predmet: naloga	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 312	16	535	285	odgovarja	oseba: učitelj -[odgovarja]-> oseba: moški	»Tudi ne,« je rekel učitelj. »Hja,« je rekel moški in strogo premeril učitelja. »Mačka pa imate, kaj?« »Ja, imamo,« je rekel učitelj. »Pa veš kaj ta maček dela?« je jezno vprašal moški »Ne,« je plaho odkimal učitelj. »Potem ti bom jaz povedal,« je rekel moški. »Ptičke ubija. Včeraj je požrl našega kanarčka. Povej očku in mami, da je bilo to prvič in zadnjič.
> 313	16	230	427	ubija	žival: mačka -[ubija]-> žival: ptičke	»Tudi ne,« je rekel učitelj. »Hja,« je rekel moški in strogo premeril učitelja. »Mačka pa imate, kaj?« »Ja, imamo,« je rekel učitelj. »Pa veš kaj ta maček dela?« je jezno vprašal moški »Ne,« je plaho odkimal učitelj. »Potem ti bom jaz povedal,« je rekel moški. »Ptičke ubija. Včeraj je požrl našega kanarčka. Povej očku in mami, da je bilo to prvič in zadnjič.
> 314	16	230	176	požre	žival: mačka -[požre]-> žival: kanarček	»Tudi ne,« je rekel učitelj. »Hja,« je rekel moški in strogo premeril učitelja. »Mačka pa imate, kaj?« »Ja, imamo,« je rekel učitelj. »Pa veš kaj ta maček dela?« je jezno vprašal moški »Ne,« je plaho odkimal učitelj. »Potem ti bom jaz povedal,« je rekel moški. »Ptičke ubija. Včeraj je požrl našega kanarčka. Povej očku in mami, da je bilo to prvič in zadnjič.
> 315	19	48	385	zamisli se	oseba: Piki -[zamisli se]-> predmet: poteza	Učitelj je imel bele ﬁgure in je potegnil kmeta pred kraljem za dve polji naprej. Piki je z druge strani napravil enako potezo. Potem je učitelj povlekel lovca in tudi Piki je povlekel lovca. Učitelj je skočil s konjem in tudi Piki je skočil s konjem. »Nikar me ne posnemaj,« je rekel učitelj, »če ne, boš kmalu izgubil.« Igrala sta naprej in oba naredila malo rošado. Potem je učitelj vzel Pikiju kmeta. Piki se je globoko zamislil.
> 316	20	48	186	požre	oseba: Piki -[požre]-> predmet: kmet	Učitelj je postal živčen: »Kaj pa toliko premišljuješ, požri kmeta, pa konec.« Piki se je malo obotavljal, potem pa vprašal: »Misliš resno?« »Seveda,« je rekel učitelj. »No, daj že.« Piki je s tresočo se taco vzel belega kmeta in postavil črnega na njegovo polje. Učitelj se je zagledal v šahovnico, Piki pa je pogledal kmeta, ki ga je držal v taci, potem pa skomignil z rameni in ga po tihem požrl.
> 317	23	48	523	ima figurko	oseba: Piki -[ima figurko]-> figurka: trdnjava	S trdnjavo je napadel belega kralja, in medtem ko se je učitelj umikal, je smuknil z deske svojega kralja in ga v trenutku požrl. Pri tem je kazal čisto nedolžen obraz. Učitelj se je pripodil s kraljico, podrl Pikijevo trdnjavo in rekel: »Mat.« »Ni mat,« je rekel Piki. »Kako da ne?« je rekel učitelj. Potem je opazil, da črnega kralja ni na šahovnici. »Kje pa imaš kralja? Saj je ravnokar stal tukaj.
> 318	24	48	500	požre	oseba: Piki -[požre]-> figurka: svoj kralj	Skril si ga. Sram te bodi. Tak šahist! Takoj ga daj sem.« »Ne morem,« je rekel Piki. »Kako ne moreš?« je vprašal učitelj »Požrl sem ga,« je priznal Piki. »Žreš lahko samo nasprotnikove ﬁgure, ne svojih,« je rekel učitelj. »Kljub vsemu si torej mat. Greva še eno partijo. Zdaj imaš ti bele.« »Nimam jih,« je rekel Piki. »Kako jih nimaš?« »Požrl sem jih.
> 319	25	535	48	vpraša	oseba: učitelj -[vpraša]-> oseba: Piki	« Šele zdaj je učitelj razumel za kaj gre. Belih ﬁgur, ki jih je Piki pobral, ni bilo nikjer. »Zakaj si jih pa požrl?« je vprašal učitelj. »Saj si mi vendar sam rekel, naj požrem kmeta, potem pa sem požrl še druge,« je rekel Piki. »Kaj bova pa zdaj?« je rekel učitelj. »Kako pa naj zdaj šahirava?« Piki je rekel: »Prosi očka, naj ti kupi nov šah.
> 320	27	48	244	opisuje	oseba: Piki -[opisuje]-> oseba: medvedja mamica	Tudi vse druge medvedke.« »Medvedja mamica, praviš?« se je čudil učitelj. »Prvič slišim. Povej mi kaj o njej.« »Medvedja mamica je šivilja, ki šiva medvedke,« je rekel Piki. »Vsak dan naredi enega in jih dela cel mesec, tako da sedi na koncu meseca na polici trideset medvedkov. Saj ima mesec trideset dni, kajne?« »Ne vsak,« je rekel učitelj. »Sicer pa ni važno,« je rekel Piki.
> 321	27	244	651	deluje	oseba: medvedja mamica -[deluje]-> poklic: šivilja	Tudi vse druge medvedke.« »Medvedja mamica, praviš?« se je čudil učitelj. »Prvič slišim. Povej mi kaj o njej.« »Medvedja mamica je šivilja, ki šiva medvedke,« je rekel Piki. »Vsak dan naredi enega in jih dela cel mesec, tako da sedi na koncu meseca na polici trideset medvedkov. Saj ima mesec trideset dni, kajne?« »Ne vsak,« je rekel učitelj. »Sicer pa ni važno,« je rekel Piki.
> 322	29	48	265	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: mehek	»Ne,« je rekel učitelj. »Tisti v živalskem vrtu je rumen. »No, vidiš,« je nadaljeval Piki. »Sicer pa me levi ne zanimajo. Govoriva o medvedji mamici. Mene je naphala z vato. Zato sem tako mehek. Samo Nekaj nas je bilo takih. Drugi so bili nabasani z morsko travo ali žagovino. Sedel sem na polici in jo opazoval. Kako je samo znala sukati škarje, ko je rezala blago za podlogo in kožušček.
> 323	30	244	369	postavi	oseba: medvedja mamica -[postavi]-> prostor: polica	Švrk, švrk, švrk -telo, švrk, švrk -roke, švrk, švrk -noge, pa še švrc. Švrc -ušesa in kožuh je bil pripravljen. Potem je v podlogo nabasala vato ali morsko travo, prišila nanjo kožuh, pripela k telesu noge, roke in glavo, na glavo pa še smrček, ušesa in oči. Ta ali oni medvedek je dobil tudi pentljo okrog vratu. Ko je bil sešit, si ga je medvedja mamica še enkrat skrbno ogledala, ga pokrtačila in postavila na polico.
> 324	85	48	323	se smeji	oseba: Piki -[se smeji]-> predmet: ogledala	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 325	85	19	672	ogleduje	oseba: Jupiter -[ogleduje]-> predmet: železnica	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 326	85	672	444	teče	predmet: železnica -[teče]-> prostor: ribnik	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 327	85	208	444	plava	predmet: ladjice -[plava]-> prostor: ribnik	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 328	87	48	476	želi	oseba: Piki -[želi]-> predmet: smrt	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 329	87	19	48	se smeji	oseba: Jupiter -[se smeji]-> oseba: Piki	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 330	88	476	51	se iztrga	predmet: smrt -[se iztrga]-> oseba: Piki in Jupiter	»Ko te poboža,« je rekel Piki, »zgrabi z vso močjo. »Zanesi se name,« je zamrmral Jupiter. Spet sta se peljala skoz grmenje in bliskanje in napeto čakala na pravi trenutek. V Dvorani smrti sta potem zagrabila. V tem hipu se je Hiša strahov prislužila svoje ime. Smrt je strašno zarjula, se iztrgala Pikiju in Jupitru iz rok ter se skoz streho pognala iz hiše.
> 331	90	249	483	ima	skupina: medvedje -[ima]-> predmet: spominske knjige	Bil je strašno jezen na smrt, ki je padla v ribnik, zaradi česar je moral tri ure drgniti parket v dnevni sobi. Spominske knjige Na lepem so vsi medvedje imeli spominske knjige. Pri pouku je kar naprej nekaj šumelo in krožilo pod klopmi. Ko je učitelj pri računstvu vprašal Benjamina: »Koliko je ena in ena?« je ta odgovoril: »Ena in ena je dve-nikar ne pozabi na me!« »Ne bom,« je rekel učitelj in mu zapisal velik minus v vedenju.
> 332	92	535	555	prebere	oseba: učitelj -[prebere]-> vsebina: verzi	Učitelju so bili verzi všeč, dvakrat jih je prebral in malo je manjkalo, pa bi Pikija pohvalil. Vendar se je še pravi čas spomnil, da je učence kaznoval, in tako je z resnim obrazom segel po drugi spominski knjigi. Bila je vezana v rdeče usnje in na platnicah je pisalo Timika. Knjiga je bila skoraj polna, nekateri medvedje so se vpisali celo po večkrat. Na začetku je bila okorno narisana ladjica, zraven pa verzi: Nisem pesnik ne risar, kaj ti naj poklonim v dar?
> 333	92	482	555	vsebuje	predmet: spominska knjiga -[vsebuje]-> vsebina: verzi	Učitelju so bili verzi všeč, dvakrat jih je prebral in malo je manjkalo, pa bi Pikija pohvalil. Vendar se je še pravi čas spomnil, da je učence kaznoval, in tako je z resnim obrazom segel po drugi spominski knjigi. Bila je vezana v rdeče usnje in na platnicah je pisalo Timika. Knjiga je bila skoraj polna, nekateri medvedje so se vpisali celo po večkrat. Na začetku je bila okorno narisana ladjica, zraven pa verzi: Nisem pesnik ne risar, kaj ti naj poklonim v dar?
> 334	95	73	535	prosi	oseba: Timika -[prosi]-> oseba: učitelj	»Upam, da ne bosta tudi tam uvedla postajališč,« je zase rekel učitelj. Medtem je zazvonilo. Medvedje so pospravili stvari in učitelj je moral prenehati z branjem spominskih knjig. Ozrl se je po razredu in vprašal: »Ste napisali?« »Smo,« so odgovorili medvedje v zboru. Potem se je vzdignila Timika in rekla: »Tovariš učitelj, lepo prosim, če bi mi kaj napisali v spominsko!« »Meni tudi, meni tudi,« so se oglasili še drugi medvedje.
> 335	96	535	272	zahteva	oseba: učitelj -[zahteva]-> značilnost: mir	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 336	96	150	483	ima	oseba: govorec -[ima]-> predmet: spominske knjige	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 337	99	254	410	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: preskakovanje ovir	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 338	99	254	382	izvaja	skupina: medvedji gasilci -[izvaja]-> dejanje: postavljanje lestev	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 339	101	64	408	meni	oseba: Poveljnik -[meni]-> značilnost: preizkušanje znanja	Poveljnik je rekel, da bi četi zelo koristile »vroče vaje«, to se pravi, gašenje »požara« v peči dnevne sobe, vendar mu tega kot višji gasilski inšpektor nisem mogel dovoliti. Približala se je pomlad. Nehali smo kuriti peči in nevarnost požarov se je zmanjšala skoraj na ničlo. A poveljnik je menil, da je treba znanje preizkusiti, in tako je četa v kopalnici priredila gasilski miting pod nazivom POŽAR V NBOTIČNIKU. Prepričal sem se, da je moštvo odlično izurjeno.
> 340	102	526	138	utihne	predmet: trobent -[utihne]-> dogodek: gasilska akcija	Trobent je komaj dobro utihnila, ko je že pridrvel izza ovinka gasilski avto in s presunljivim »goo-rii, goo-rii« odhitel na kraj požara. Vrstila so se povelja: »Sestavite lestve! Razvijte cevi! Priključite vodo!« Za nebotičnik je služil veliki vodogrelec v kotu kopalnice. Lestve so se pognale do vrhnjih nadstropij, po njih sta splezala Filip in Benjamin ter začela reševati »ogrožene prebivalce«.
> 341	103	48	283	pripravi	oseba: Piki -[pripravi]-> predmet: motorno brizgalno	Metala sta jih v globino, kjer so jih štirje gasilci spretno lovili v ponjavo, Medtem je višji gasilec Piki pripravil motorno brizgalno. Na vodovodno pipo je nataknil dolgo cev ter z roba umivalnika usmeril močan curek proti »plamenom«. Žal mu je na mokrih tleh spodrsnil in je padel, vendar pa cevi tudi med padcem ni izpustil iz rok. Po nesreči je curek zadel reševalca Benjamina in Filipa, ki sta iz vrtoglave višine strmoglavila na ponjavo, s katere se je samo trenutek prej pobral Piki.
> 342	105	48	562	pomisli	oseba: Piki -[pomisli]-> izkušnja: vodeni krst	»Lahko bi se reklo tudi vodeni krst,« je pomislil Piki, vendar zaradi še zmeraj jeznih gasilcev tega ni povedal na glas. Po govoru je poveljnik razdelil gasilske značke, Timika pa je vsakemu pripela na prsi rdeč nagelj. Od takrat se pri nas več ne bojimo požarov. Piki vrtnar Učiteljeva mama je sklenila, da bo posadila v lončke nekaj spomladanskih cvetic. Iz semenarne je prinesla vrečice s čebulicami različnih velikosti.
> 343	105	77	575	prinaša	oseba: Učiteljeva mama -[prinaša]-> predmet: vrečice s čebulicami	»Lahko bi se reklo tudi vodeni krst,« je pomislil Piki, vendar zaradi še zmeraj jeznih gasilcev tega ni povedal na glas. Po govoru je poveljnik razdelil gasilske značke, Timika pa je vsakemu pripela na prsi rdeč nagelj. Od takrat se pri nas več ne bojimo požarov. Piki vrtnar Učiteljeva mama je sklenila, da bo posadila v lončke nekaj spomladanskih cvetic. Iz semenarne je prinesla vrečice s čebulicami različnih velikosti.
> 344	106	574	636	vsebuje	predmet: vrečica -[vsebuje]-> predmet: čebulice	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 345	106	537	597	prebarvata	skupina: učitelj in Piki -[prebarvata]-> predmet: zabojčke	Na vsaki vrečici je pisalo, koliko čebulic je v njej, kakšne rože bodo zrasle iz njih in kakšne barve bodo cvetovi. Ker sta se učitelj in Piki za sajenje zelo zanimala, ju je mama povabila v vrtnarski krožek. Učitelj je postal njen pomočnik, Piki pa vrtnarski vajenec. Mama je šla v vrtnarijo po zemljo in nove lončke, učitelj in Piki pa sta odgrnila stare zabojčke in jih na novo zeleno prebarvala.
> 346	107	48	606	ima težavo	oseba: Piki -[ima težavo]-> značilnost: zaspanje	Sklenili so, da bodo čebulice posadili v soboto dopoldne, ko bodo prosti in ne bodo imeli drugih skrbi. Tisto noč je bilo zadušljivo, tako da učitelj in Piki dolgo nista mogla zaspati. Dvakrat sta šla pit slatino, pa ni nič pomagalo. Ko smo vsi drugi že spali, sta se še zmeraj premetavala po postelji. »Ne morem in ne morem zaspati,« je vzdihnil učitelj. »Jaz tudi ne,« je zamomljal Piki in si obrisal potno čelo.
> 347	108	535	59	odzove	oseba: učitelj -[odzove]-> predloga: Pikijeva predloga	»Ko bi se lahko vsaj za baterijo igrala.« »Kaj ni pod blazino?« »Je, ampak je crknila žarnice.« Utihnila sta in molčala, dokler ni Piki zašepetal: »Kaj ko bi šla sadit rože?« »Hm,« je zagodel učitelj, »ni slaba misel.« Malo sta še počakala, potem pa je učitelj položil kazalec na usta in po tihem odgrnil odejo. Smuknila sta iz postelje in se po prstih odplazila v kuhinjo. Tam sta najprej pogrnila mizo s starimi časopisi.
> 348	31	244	264	se pogovarja	oseba: medvedja mamica -[se pogovarja]-> predmet: medvedki	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 349	32	244	288	dela	oseba: medvedja mamica -[dela]-> oseba: možakar	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 350	35	50	393	pošlje pismo	oseba: Piki Jakob -[pošlje pismo]-> prostor: pošta	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 351	36	48	4	piše	oseba: Piki -[piše]-> oseba: Berenson	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 352	36	242	233	jedajo	oseba: medvedi v Parizu -[jedajo]-> značilnost: med	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 353	37	535	23	poisal	oseba: učitelj -[poisal]-> prostor: Ljubljana	Moj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«
> 354	38	50	394	prejme pismo	oseba: Piki Jakob -[prejme pismo]-> oseba: poštar	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 355	39	48	128	je član	oseba: Piki -[je član]-> skupina: družina	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 356	40	48	545	ima težavo	oseba: Piki -[ima težavo]-> značilnost: uši	Zjutraj ga je začelo trgati po ušesih in zato smo ga obvezali z ruto. Končiča rute sta bingljala z glave kot velika uhlja, kot da Piki ne bi bil medved, ampak zajec. Potem smo se odpravili. Po poti je učitelj razlagal, kako se je treba vesti pri zobozdravniku. »Zobozdravnik je tvoj prijatelj,« je rekel Pikiju. »Seveda,« je potrdil Piki. »Če te bo malo bolelo,« je nadaljeval učitelj, »nikar tako ne tuli, da bo pobegnilo pol čakalnice.«
> 357	45	48	623	ima zob	oseba: Piki -[ima zob]-> predmet: zob	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 358	45	626	48	pregleda	oseba: zobozdravnik -[pregleda]-> oseba: Piki	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 359	46	246	662	organizira	prostor: medvedja šola -[organizira]-> dogodek: športni dan	Ko smo nekaj časa molče korakali, je rekel učitelj: »Piki, zakaj si ugrizni zobozdravnika?« »Saj si mi rekel, da naj stisnem zobe,« je odgovoril Piki. Spogledali smo se in se zasmejali. Učitelj pa se je obrnil k meni in rekel: »Glej, da ga drugič ne ugrizneš še ti.« Športni dan V medvedji šoli so imeli športni dan. Najprej je bila na vrsti vožnja z žičnico. Učitelj je napeljal vrv od kljuke na vratih do kljuke na oknu.
> 360	47	225	174	sestavi	oseba: matador -[sestavi]-> predmet: kabino	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 361	47	73	529	šeži	oseba: Timika -[šeži]-> predmet: uho	Iz matadorjevih kock je sestavil kabino, ki je drsela po vrvi na velikem kolesu čisto kakor pri pravi žičnici. Kabina je bila majhna in zato se je moral peljati vsak medved posebej, pa še tako so cepali dol kot zrele hruške. Seveda se ni nobenemu nič zgodilo. Samo Timika si je priščipnila uho in Josip Jupiter si je razparal levo hlačnico. Ampak kaj takega se zgodi na vsake poštenem športnem dnevu. Potem je učitelj naznanil, da bodo imeli spomladanski kros ali tek čez drn in strn.
> 362	49	132	215	izgubi	predmet: fikus -[izgubi]-> predmet: lista	Najprej so tekli skoz brezov gaj ali po domače skoz dnevno sobo, in ker so se v gneči suvali, so podrli nekaj dreves, ki jih je učitelj postavil ob progi, med njimi košati hrast ali po domače ﬁkus, ki je pri tem izgubil dva lista. Čez pusto planjavo ali po domače hodnik so pritekli brez nezgode. Zato pa so imeli hude težave v močvirnih predelih ali po domače v kopalnici. Lovili so ravnotežje po ozkih brveh in Filip je padel v ribnik ali po domače banjo in je prenehal s tekmovanjem.
> 363	50	48	510	teče	oseba: Piki -[teče]-> prostor: temna goščava	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 364	50	48	435	teče	oseba: Piki -[teče]-> predmet: razmetane učiteljeve igrače	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 365	51	263	162	vrže	oseba: medvedji športniki -[vrže]-> žival: hudi tiger	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 366	52	48	106	prileti	oseba: Piki -[prileti]-> prostor: cilj	Zato je s Pikijem na hrbtu predrvel vse sobe, vendar ni nikjer našel odprtega okna, ker je učitelj okna pred tekmovanjem iz previdnosti zaprl Zato se je pognal proti kuhinji. Ko je tam zagledal učitelja, je zavrl z vsemi štirimi zavorami ali po domače nogami in Piki je v velikem loku priletel z njegovega hrbta naravnost na cilj. Precej časa je poteklo, preden so za njima upehani pritekli tudi drugi medvedje.
> 367	53	48	160	razdeli	oseba: Piki -[razdeli]-> predmet: hruško	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 368	55	70	48	svetuje	oseba: Stari Marko -[svetuje]-> oseba: Piki	»Mogoče imaš vročino,« je zamomljal Stari Marko. Piki je zajavkal: »Mogoče res.« »Ali pa sončarico,« je rekel Stari Marko. Piki je prestrašeno vzkliknil: »Kaj?« »Ali celo kolero,« je nadaljeval Stari Marko. »Solit se pojdi,« se je razjezil Piki, »za norca me imaš, namesto da bi mi pomagal.« »Bah,« je rekel Stari Marko. »Skuhaj si čaj in pojej tableto.
> 369	57	48	306	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: neznanje	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 370	58	48	580	ima lastnost	oseba: Piki -[ima lastnost]-> bolezen: vročina	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 371	60	535	48	pojasnjuje	oseba: učitelj -[pojasnjuje]-> oseba: Piki	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 372	60	535	48	pomaga	oseba: učitelj -[pomaga]-> oseba: Piki	»Nič 'vidiš',« je odgovoril učitelj. »To sta dve različni vročini. Ena je zunaj, druga pa je znotraj. Če je znotraj, imaš ti vročino, če je zunaj, pa ima vročina tebe. Tako je to.« »Torej im vročina mene,« je rekel Piki. Tedaj je učitelj namočil Pikija v kopalno kad, kjer se je tako ohladil, da smo ga morali zvečer greti in sušiti pri peči. Na počitnice Šola se je končala.
> 373	61	535	392	se pripravlja	oseba: učitelj -[se pripravlja]-> dogodek: počitnice	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 374	61	48	122	ima izkušnjo	oseba: Piki -[ima izkušnjo]-> čustvo: dolgčas	Piki ni imel nobene enke, nobene dvojke, nobene trojke, tudi nobene štirke, ampak čiste petke. Takšnega medveda bi težko našli celo v živalskem vrtu, kaj šele kje drugje. Ampak Piki je Piki, znameniti medved. Začeli smo se pripravljati za počitnice. Učitelj je sklenil, da bo vzel s seboj tudi Pikija. Lani smo ga pustili doma, pa mu je bilo dolgčas. Ampak lani je bil Piki še predšolski medvedek, takšni pa se radi zgubijo in padejo v morje. Letos je seveda drugače.
> 375	62	252	392	gre na	skupina: medvedji -[gre na]-> dogodek: počitnice	Letos je že pravi fant in z učiteljem sva mu kupila medvedji kovček, v katerega zdaj spravlja svojo medvedjo prtljaso. Seveda gredo na počitnice tudi drugi medvedje. Niso sicer vsi taki odličnjaki kot Piki, a popravnega izpita nima nobeden. To pa je glavno. Učitelj me je prepričal, da zaradi njih ne bo treba najeti posebnega avtobusa, ampak da bodo čisto zadovoljni s prtljažnikom na strehi našega tisočtristo. »Pa naj bo,« sem rekel, sam kaj drugega tudi ni preostalo.
> 376	63	150	614	se spominja	oseba: govorec -[se spominja]-> dogodek: zgodba o mačku	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 377	64	535	48	opazuje	oseba: učitelj -[opazuje]-> oseba: Piki	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 378	65	48	486	sedel	oseba: Piki -[sedel]-> prostor: sprednji sedež	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 379	66	48	471	se veseli	oseba: Piki -[se veseli]-> hrana: sladoled	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 380	66	48	433	podpiše	oseba: Piki -[podpiše]-> dokument: razglednica	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 381	67	48	656	želi postati	oseba: Piki -[želi postati]-> značilnost: šofer medvedjega avtobusa	Zato se nisem preveč začudil, ko je po počitnicah rekel učitelju, da bi se rad naučil voziti in da bi rad postal šofer medvedjega avtobusa. Učitelj ni imel nič proti, pripomnil je le, da bo treba najti dobrega inštruktorja. Po krajšem premisleku je ugotovil, da za zdaj pri hiši ni boljšega od mene, in tako sem na lepem postal medvedji vozniški učitelj. Piki se je vpisal v tečaj in ker je bil edini učenec, je hitro napredoval. Najprej sva se učila prometne znake.
> 382	69	48	364	dodajal in odvzemal	oseba: Piki -[dodajal in odvzemal]-> značilnost: plin	Učitelj mu je prijazno razložil, da so se v starih škatlah izučili najboljši šoferji. Za zgled je postavil mene. Piki je skomignil z rameni in odpeljala sva se na avtodrom sredi kuhinje. Prva ura je bila precej naporna. Kar naprej sva se zadevala ob mizo in stole. Vendar se je Piki kmalu naučil speljevanja in ustavljanja in že čez nekaj dni je spretno menjaval prestave ter dodajal in odvzemal plin.
> 383	71	150	48	prepričal	oseba: govorec -[prepričal]-> oseba: Piki	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 384	72	48	441	razkril	oseba: Piki -[razkril]-> značilnost: resnica	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 385	72	48	181	zatrobil	oseba: Piki -[zatrobil]-> značilnost: klik	»Nima okvar,« je ponovil Piki, »ker to sploh ni tovornjak.« »Kaj pa je potem?« sem rekel in si popravil očala. »Naš maček,« je rekel Piki. »Oči se mu svetijo. Ampak jaz bom zdaj zatrobil, pa čeprav ni po pravilih.« Bila sva že čisto blizu »tovornjaka« in Piki je pošteno zatrobil. Maček je poskočil, kot da bi šinila vanj elektrika, in jo ucvrl s četrto brzino.
> 386	73	48	445	izvajal	oseba: Piki -[izvajal]-> značilnost: ritenska vožnja	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 387	74	48	520	nabral	oseba: Piki -[nabral]-> značilnost: točke	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 388	74	48	568	delal	oseba: Piki -[delal]-> poklic: voznik avtobusa	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 389	77	660	27	vstopili	oseba: šolarji -[vstopili]-> prostor: MEDVEDJI DOM	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 390	78	37	85	dejstvo	oseba: Medvedje -[dejstvo]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 391	78	32	85	potovanje	oseba: Marko Prvi -[potovanje]-> prostor: avtobus	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 392	79	12	69	govori	oseba: Filip -[govori]-> oseba: Sprevodnik	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 393	80	48	229	vidi	oseba: Piki -[vidi]-> predmet: mačji rep	»Tu imaš sprevodnika,« je rekel Filip in počil Josipa Jupitra za uho. Začelo se je prerivanje, suvanje in slednjič vsesplošni pretep. Zvezki, čepice in dežniki so frčali po avtobusu, da je kar žvižgalo. Piki je vozil s polno paro. Ko je pridrvel izza ovinka, je pri postajališču MAČJA SKLEDA zagledal veliko naravno oviro, ki je pravkar lokala mleko. Piki je zavrl, vendar se trčenju ni mogel izogniti. Zapeljal je čez mačji rep. Njegov lastnik je divje poskočil in prevrnil avtobus.
> 394	136	7	204	vpil	oseba: Dirigent -[vpil]-> značilnost: krulba	Piki je postal vodja moškega pevskega zbora, samih basistov brez posluha. Nekega dne sem poslušal, ko so vadili pesem o dvanajstih razbojnikih. Peli so jo narobe, a tako glasno, kakor da je razbojnikov najmanj štiriindvajset. Dirigent je trkal s paličico po pultu in vpil: »To je krulba, ne petje. Gozdne medvede boste zbudili tri tedne prezgodaj!« Ko je slednjič napočila Velika Medvednica, je bila ne samo v koledarju, ampak tudi v naravi že prava pomlad.
> 395	141	258	308	zapel	skupina: medvedji pevski zbor -[zapel]-> značilnost: nove pesmi	Zapel je same nove pesmi: »Ko medved zjutraj v šolo gre«, »Medene lonce ližemo«, »Medvedje hrabri smo gasilci« in »Pomald -medvedji letni čas«. Po končani proslavi je bila pogostitev. Vsak medved je dobil eno minihrenovko in en makismed. Za učitelja in goste pa je poskrbela učiteljeva mama s slavnostnim kosilom, tako dobrim, da bi najraje vsak dan praznovali Veliko Medvednico. Potovanja Nekega dne je prišel učitelj k meni in rekel: »Lahko bi šli v Pariz.« »Kam?
> 396	145	535	150	se pogovarja	oseba: učitelj -[se pogovarja]-> oseba: govorec	»V pravljici,« je s posmehom rekel učitelj. »Kako pa se pride v pravljico? Bi nas ti peljal z avtom?« »Mogoče,« sem rekel. »Ampak v pravljico se pride najbolje peš. Kdor preveč hiti, se odpelje mimo.« »Raje bi šel v Pariz,« je rekel učitelj. »Piki tudi.« »Tudi Pariz je pravljica,« sem rekel po kratkem molku. »In seveda severni tečaj tudi. In Afrika tudi.« Učitelj me je pogledal.
> 397	147	535	674	potrdi	oseba: učitelj -[potrdi]-> prostor: živalski vrt	»Veš,« je rekel učitelj čez čas, »pravzaprav Pikiju niti ni toliko do Pariza. Pogovarjala sva se pač.« »Tudi midva se pogovarjava, ne?« »Seveda. Živalski vrt pa vseeno drži?« »Jasno. Če sem rekel, bomo šli.« In smo šli. In tako potujem, v resnici in v sanjah, na severni tečaj in pod Rožnik, smejemo se opicam v kletkah in sedimo na saneh, ki jih vlečejo psi skoz polarno pokrajino.
> 398	111	48	535	pomirja	oseba: Piki -[pomirja]-> oseba: učitelj	»To vem tudi jaz,« je rekel učitelj, »a zdaj je važno, v katerem lončku so.« »Lahko jih spet izkopljeva,« je predlagal Piki. »Kaj se ti meša,« se je zgrozil učitelj. »Se bova že česa spomnila,« je rekel Piki pomirjevalno. Ko je drugo jutro mama stopila v kuhinjo, so jo presenetili zabojčki in lončki z napisanimi tablicami, ki so bile zataknjene v prst.
> 399	114	447	275	se spreminjajo	predmet: rožnate hijacinte -[se spreminjajo]-> predmet: modre hijacinte	Vprašal sem učitelja, ali se mu ne zdi potrebno, da bi o enkratnem primeru, ko so iz tulipanove čebulice zrasli zvončki, obvestili vrtnarsko društvo. Učitelju se to ni zdelo potrebno ne zdaj ne pozneje, ko so se rožnate hijacinte spreminjale v modre, rumeni krokusi v bele in zvončki v rdeče tulipane. Vrtnarja sta vztrajno zatrjevala, da sta na tablice napisala prav tisto, kar je stalo na vrečkah iz katerih sta jemala čebulice. »Tu ima vmes svoje kremplje naš maček,« je rekel učitelj.
> 400	116	535	144	ogrožen	oseba: učitelj -[ogrožen]-> predmet: gnila jajca in paradižnike	Na vežna vrata je obesil velik oglas: Cirkus BEŽIGRAD vabi k predstavi ob 16. uri. Nastopajo vrvohodci, klovni, žonglerji, dresirani tigri in cirkuška godba. Pred nastopom ogled živalskega vrta. Vabljeni! Ogledal sem si vabilo in opozoril učitelja, naj se nikar ne šali z gledalci. »Če jih misliš povleči za os,« sem rekel, »gledalci ne bodo le žvižgali, ampak bodo tudi metali gnila jajca in paradižnike. Ob takih priložnostih je najljubša tarča direktor. Verjetno si to ti?«
> 401	117	535	150	pomirja	oseba: učitelj -[pomirja]-> oseba: govorec	Učitelj je pokimal in rekel: »Nikar ne skrbi, vse bo v redu.« »Imaš klovne?« sem vprašal. Učitelj je pokimal. »Pa tigre?« Učitelj je spet pokimal. »Pa žonglerje?« »Žongler boš ti,« je rekel učitelj. »Jaz?« »Seveda, saj na počitnicah zmeraj žongliraš z balinčki.« »Kot veš, samo s tremi kroglami.« »Za moj cirkus to zadostuje,« je rekel direktor. »Tu imaš krogle.
> 402	117	535	150	imenuje	oseba: učitelj -[imenuje]-> oseba: govorec	Učitelj je pokimal in rekel: »Nikar ne skrbi, vse bo v redu.« »Imaš klovne?« sem vprašal. Učitelj je pokimal. »Pa tigre?« Učitelj je spet pokimal. »Pa žonglerje?« »Žongler boš ti,« je rekel učitelj. »Jaz?« »Seveda, saj na počitnicah zmeraj žongliraš z balinčki.« »Kot veš, samo s tremi kroglami.« »Za moj cirkus to zadostuje,« je rekel direktor. »Tu imaš krogle.
> 403	117	117	201	daje	oseba: direktor -[daje]-> predmet: krogle	Učitelj je pokimal in rekel: »Nikar ne skrbi, vse bo v redu.« »Imaš klovne?« sem vprašal. Učitelj je pokimal. »Pa tigre?« Učitelj je spet pokimal. »Pa žonglerje?« »Žongler boš ti,« je rekel učitelj. »Jaz?« »Seveda, saj na počitnicah zmeraj žongliraš z balinčki.« »Kot veš, samo s tremi kroglami.« »Za moj cirkus to zadostuje,« je rekel direktor. »Tu imaš krogle.
> 404	118	150	548	svetuje	oseba: govorec -[svetuje]-> dejanje: vajanje	Lahko še pol ure vadiš. Jaz imam še opravke.« Ob pol štirih si je šlo občinstvo ogledat znamenite in redke živali, kakršnih nima noben cirkus na svetu. Medvedje so imeli vstop prost, ljudje pa smo plačali po en dinar. Živalski vrt ni bil velik, zato pa zanimiv. V središču je stala kletka z zelenima papagajema, okrog nje pa so pravilno razporejeni sedeli trije tigri in en črn lev. Največji tiger je bil precej podoben našemu mačku, druge tri zveri pa njegovim prijateljem iz hiše in bližnje soseščine.
> 405	118	314	674	ogleda	oseba: občinstvo -[ogleda]-> prostor: živalski vrt	Lahko še pol ure vadiš. Jaz imam še opravke.« Ob pol štirih si je šlo občinstvo ogledat znamenite in redke živali, kakršnih nima noben cirkus na svetu. Medvedje so imeli vstop prost, ljudje pa smo plačali po en dinar. Živalski vrt ni bil velik, zato pa zanimiv. V središču je stala kletka z zelenima papagajema, okrog nje pa so pravilno razporejeni sedeli trije tigri in en črn lev. Največji tiger je bil precej podoben našemu mačku, druge tri zveri pa njegovim prijateljem iz hiše in bližnje soseščine.
> 406	119	644	674	zbeža	žival: črni lev -[zbeža]-> prostor: živalski vrt	Sedeli so čisto pri miru in napeto opazovali, kaj se dogaja v kletki. Črni lev je nekajkrat stegnil taco, a jo je brž umaknil, ko je začutil trdoto papagajevega kljuna. Ker sem mu po nerodnosti stopil na rep, je divje zavreščal ter jo ubral iz živalskega vrta, za njim pa še dva njegova prijatelja. Zbežati je hotel tudi naš tiger, vendar ga je direktor pravočasno ujel in spravil na varno. Ogled živalskega vrta je bi s tem končan in občinstvo je odšlo na predstavo.
> 407	121	213	674	pobegnejo	žival: lev in tigri -[pobegnejo]-> prostor: živalski vrt	Pošteno sem se namučil, preden sem svoje tri krogle dvajsetkrat zavrtel, ne da bi mi katera padla na tla. Zato pa mi je potem, ko sem se priklanjal občinstvu, padla ena iz žepa na kurje oko. Na vrsti je bila zadnja in glavna točka spored: dresura tigrov. Direktor je povedal, da so en lev in dva tigra pobegnili, ampak da to nič ne de, ker preostali tiger zaleže za štiri.
> 408	121	409	665	zaleže	žival: preostali tiger -[zaleže]-> žival: štiri tigra	Pošteno sem se namučil, preden sem svoje tri krogle dvajsetkrat zavrtel, ne da bi mi katera padla na tla. Zato pa mi je potem, ko sem se priklanjal občinstvu, padla ena iz žepa na kurje oko. Na vrsti je bila zadnja in glavna točka spored: dresura tigrov. Direktor je povedal, da so en lev in dva tigra pobegnili, ampak da to nič ne de, ker preostali tiger zaleže za štiri.
> 409	122	513	313	skok	žival: tiger -[skok]-> predmet: obroč	Prosil je za popolno tišino, ker je zver zelo živčna in bi lahko pobegnila, gledalcem pa bi tako ušla najboljša točka sporeda. Občinstvo je zadržalo dih. Na direktorjev znak je Piki splezal na postelje in vzdignil velik obroč. Direktor je zvil iz papirja kroglo, jo dal povohati tigru, potem pa jo vrgel skoz obroč čez obe postelji. Tiger se je v elegantnem skoku pognal skoz obroč, preletel postelji in pristal na drugi strani na tleh. Pograbil je kroglo in jo prinesel direktorju.
> 410	124	48	641	postane	oseba: Piki -[postane]-> članstvo: član padalskega društva	Seveda ni treba misliti, da mu je spodrsnilo na ledu ali da se je spotaknil na cesti, tudi s kolesa ni padel, še manj pa pri matematiki. Piki je postal član padalskega društva. Nekega večera smo na televiziji gledali ﬁlm o padalcih. Beli mehurčki, ki so vreli iz letal, se počasi večali ter slednjič kot ogromne napihnjene buče pristali na tleh, so bili Pikiju zelo všeč.
> 411	127	371	30	daje znak	oseba: polkovnik -[daje znak]-> oseba: Marko	Pred odskočiščem na južni strani terase so v vrsti stali Marko, Jupter, Piki in Filip v popolni padalski opremi. Po kratkem pregledu je dal polkovnik znak za začetek. Prvi se je s police pognal Stari Marko. Odskok je uspel, padalo je hitro ujelo zrak in se lepo razprostrlo. Nenadni sunek vetra pa je padalca zasukal in ga pognal proti bloku in ga odložil med kaktuse na balkonu drugega nadstropja. »Pozor!« je zaklical poveljnik.
> 412	127	390	336	opozarja	oseba: poveljnik -[opozarja]-> oseba: padalec	Pred odskočiščem na južni strani terase so v vrsti stali Marko, Jupter, Piki in Filip v popolni padalski opremi. Po kratkem pregledu je dal polkovnik znak za začetek. Prvi se je s police pognal Stari Marko. Odskok je uspel, padalo je hitro ujelo zrak in se lepo razprostrlo. Nenadni sunek vetra pa je padalca zasukal in ga pognal proti bloku in ga odložil med kaktuse na balkonu drugega nadstropja. »Pozor!« je zaklical poveljnik.
> 413	128	18	70	sreča	oseba: Josip Jupiter -[sreča]-> oseba: Stari Marko	»Zaradi bočnega vetra pritegnite vrvi, če ne, bom še vas lovil po balkonih. Naslednji!« Josip Jupiter se je lahkotno odgnal in brez težav zaplaval v globino. Ko je letel mimo drugega nadstropja, je salutiral Staremu Marku, ki se je pobiral iz kaktusov. Samo za hip je pozabil na veter, a ta se mu je brž maščeval in ga pognal čez ograjo balkona v prvem nadstropju. Polkovnik je hotel tekmovanje ustaviti, a ga je Piki preprosil, naj poskusi še z njim.
> 414	128	48	371	prosi	oseba: Piki -[prosi]-> oseba: polkovnik	»Zaradi bočnega vetra pritegnite vrvi, če ne, bom še vas lovil po balkonih. Naslednji!« Josip Jupiter se je lahkotno odgnal in brez težav zaplaval v globino. Ko je letel mimo drugega nadstropja, je salutiral Staremu Marku, ki se je pobiral iz kaktusov. Samo za hip je pozabil na veter, a ta se mu je brž maščeval in ga pognal čez ograjo balkona v prvem nadstropju. Polkovnik je hotel tekmovanje ustaviti, a ga je Piki preprosil, naj poskusi še z njim.
> 415	130	535	92	pomigne	oseba: učitelj -[pomigne]-> prostor: balkoni	»Ja, veter,« je rekel učitelj malce potlačeno. Pomignil je z glavo proti balkonom. »Treba bo iti po Marka in Jupitra. Greš z mano?« »S tabo?« sem se začudil. »No, vsaj po Marka,« je silil učitelj. »Ti ga drugače ne bodo dali?« Učitelj je skomignil z rameni. »Naj bo,« sem rekel, »pojdiva.« Pozvonila sva v drugem nadstropju. Odprla nama je stara gospa.
> 416	130	414	535	se strinja	oseba: pripovedovalec -[se strinja]-> oseba: učitelj	»Ja, veter,« je rekel učitelj malce potlačeno. Pomignil je z glavo proti balkonom. »Treba bo iti po Marka in Jupitra. Greš z mano?« »S tabo?« sem se začudil. »No, vsaj po Marka,« je silil učitelj. »Ti ga drugače ne bodo dali?« Učitelj je skomignil z rameni. »Naj bo,« sem rekel, »pojdiva.« Pozvonila sva v drugem nadstropju. Odprla nama je stara gospa.
> 417	1	50	246	hodi v	oseba: Piki Jakob -[hodi v]-> prostor: medvedja šola	Moj prijatelj Piki Jakob Kdo je Piki Piki ne stanuje v gozdu, ne v živalskem vrtu, ne v cirkusu, ne v trgovini. Piki stanuje v bloku, v četrtem nadstropju, na polici za igrače. Pikiju je ime Piki, čeprav ni pikast. Tako mu je pač ime. Ni namreč vsakdo belec, ki se Belec piše, in tudi vode ne pije vsakdo, ki se piše Vodopivec. Tako je tudi Pikiju ime Piki. Piki hodi v medvedjo šolo in ima učitelja, ki ni medved, ampak fantek.
> 418	3	73	235	je	oseba: Timika -[je]-> oseba: medved	Z njim se peljejo tudi drugi medvedi in vseh skupaj je za cel medvedji avtobus. Dvema ali trem je ime Marko. Eden je Filip in majhni medvedki je ime Timika. Potem so tukaj še Josip Jupiter, Benjamin in Floki, ki sicer ni medved, ampak pes, vendar hodi v medvedjo šolo, ker posebne pasje šole še nimamo. Z učiteljem spiva v isti sobi in zato je Piki včasih tudi leteči medved. Ko se učitelj zjutraj zbudi, pogleda, ali jaz še spim, in mi vrže medveda na glavo.
> 419	4	48	535	gre spat z	oseba: Piki -[gre spat z]-> oseba: učitelj	Piki prileti elegantno kot helikopter in me poščegeta po nosu. Tako se zbudim in zaradi tega mu včasih rečem: medvedbudilka. Zvečer gre Piki spat z učiteljem. Pripovedujeta si pravljice v medvedjem jeziku, ki ga jaz ne razumem. Kadar me ima učitelj posebno rad, položi Pikija k mojemu zglavju in, ko grem ponoči v posteljo, me Piki poboža, tako kot tudi jaz pobožam njega in učitelja. Ker ne znam medvedjega jezika, si ne pripovedujeva pravljic in hitro zaspiva. Vendar je Piki zelo izobražen.
> 420	6	221	219	dodaja	oseba: mama -[dodaja]-> značilnost: majonezo	Kot pravi kuhelmuc se je sukal po kuhinji in opazoval mamo, ki je rezala kumarice, krompir, korenček, zeleno in kolerabo. Vse te stvari jemo po navadi vsako posebej in nekatere od njih je tudi učitelj. A mama jih je pomešala ter jim dodala še gorčico in majonezo, tako da je nastala čudna godlja, ki ji pravimo francoska solata. Učitelj je strmel v čudo in mama je rekla: »Boš malo pokusil?« Učitelj je odločno odkimal: »Ne, hvala, ne bom.«
> 421	7	535	298	ima mnenje	oseba: učitelj -[ima mnenje]-> značilnost: ne maram čudnih jedi	»Samo malo poskusi,« je rekla mama, »samo eno žličko.« Učitelj je odgovoril: »Take čudne jedi mi niso všeč. Ne maram jih.« Mama je vztrajala: »Moraš se navaditi tudi na nove jedi.« Učitelj je bil drugačnega mnenja in je ponovil: »Ne bom.« Mama ni popustila: »Samo eno žličko. Saj ni strup.« Učitelj pa je rekel: »Je. Če to pojem, bom umrl.«
> 422	7	535	171	trdi	oseba: učitelj -[trdi]-> značilnost: jed je strup	»Samo malo poskusi,« je rekla mama, »samo eno žličko.« Učitelj je odgovoril: »Take čudne jedi mi niso všeč. Ne maram jih.« Mama je vztrajala: »Moraš se navaditi tudi na nove jedi.« Učitelj je bil drugačnega mnenja in je ponovil: »Ne bom.« Mama ni popustila: »Samo eno žličko. Saj ni strup.« Učitelj pa je rekel: »Je. Če to pojem, bom umrl.«
> 423	8	221	535	vpraša	oseba: mama -[vpraša]-> oseba: učitelj	Mama je postala skoraj huda: »Kaj misliš, da bodo tudi naši gostje umrli? Ali misliš, da jih hočem zastrupiti?« Učitelj je skomignil z rameni: »Ne vem. Mogoče pa.« »Le čakaj,« je rekla mama, »poklicala bom Pikija, pa boš videl, kako bo z veseljem poskusil.« Učitelj je molčal. Mam je vzela Pikija s police in ga vprašala: »Piki, ali hočeš malo francoske solate?« Piki je pokimal. »No, ali vidiš?«
> 424	9	221	535	govori	oseba: mama -[govori]-> oseba: učitelj	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 425	9	535	54	trdi	oseba: učitelj -[trdi]-> značilnost: Piki ne mara francoske solate	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 426	9	48	221	odgovarja	oseba: Piki -[odgovarja]-> oseba: mama	je rekla mama učitelju, ta pa je kar molčal. Mama je zajela žličko francoske solate in jo podržala pred Pikijevim gobčkom. Medvedek se ni ganil. »Vidiš, tudi Piki je ne mara,« je zmagoslavno rekel učitelj. Tedaj pa se je zgodil čudež. Plišasti medvedek je odprl gobček in z žličke polizal francosko solato. »Boš še, Piki?« je vprašala mama in Piki je pokimal.
> 427	10	535	221	pove	oseba: učitelj -[pove]-> oseba: mama	Tako je pojedel še drugo, tretjo in četrto žlico, potem pa se je lepo obliznil in se priklonil, kar je pomenilo: hvala. »Si videl?« je rekla mama učitelju. »Pha,« je rekel učitelj, »jasno, Piki je Francoz, Parižan. Tam vsi Žužuji jejo francosko solato, saj mi je pravil. Jaz pa nisem Žužu, ampak medvedji učitelj. Si že slišala, da bi kdaj kak medvedji učitelj jedel francosko solato?«
> 428	12	231	268	izdajajo zvok	žival: mačke -[izdajajo zvok]-> značilnost: mijavkanje	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 429	12	428	679	izdajajo zvok	žival: ptički -[izdajajo zvok]-> značilnost: žvrgolij	»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.
> 430	13	48	535	pogovarja se	oseba: Piki -[pogovarja se]-> oseba: učitelj	»Eno je šala, drugo pa šola,« je strogo rekel učitelj. »Tukaj smo v šoli. Mačke mijavkajo in nič drugega.« »Naš maček tudi žvižga,« je ugovarjal Piki. »Slišal sem ga včeraj popoldne, ko je žvižgal na balkonu.« »Kaj ne poveš,« se je posmehnil učitelj. »Ja, ravno sem pisal nalogo,« je rekel Piki, »ko sem zaslišal žvižganje. Mislil sem, da je kanarček.
> 431	15	535	285	sreča	oseba: učitelj -[sreča]-> oseba: moški	»Nadaljujmo,« je rekel učitelj. »Marko, povej …« Tedaj je pozvonilo. Učitelj je prenehal sredi stavka. Potrkal je s svinčnikom po mizi in rekel: »Takoj se vrnem. Med tem ponavljajte.« Medvedje so se zagledali v zvezke, učitelj pa je odšel v vežo. Previdno, komaj za dlan široko je odprl vrata in pokukal ven. Zunaj je stal moški iz sosednega stopnišča. »Je očka doma?« je vprašal. Učitelj je odkimal. »Pa mama?«
> 432	15	535	285	odgovarja	oseba: učitelj -[odgovarja]-> oseba: moški	»Nadaljujmo,« je rekel učitelj. »Marko, povej …« Tedaj je pozvonilo. Učitelj je prenehal sredi stavka. Potrkal je s svinčnikom po mizi in rekel: »Takoj se vrnem. Med tem ponavljajte.« Medvedje so se zagledali v zvezke, učitelj pa je odšel v vežo. Previdno, komaj za dlan široko je odprl vrata in pokukal ven. Zunaj je stal moški iz sosednega stopnišča. »Je očka doma?« je vprašal. Učitelj je odkimal. »Pa mama?«
> 433	17	231	678	žvižgajo	žival: mačke -[žvižgajo]-> značilnost: žvižganje	Če se še enkrat prikaže, ga bom predelal v klobase. Razumeš?« Učitelj je pokimal in zaprl vrata. Vrnil se je v razred in rekel: »Za danes smo končali. Lahko greste. Piki, ti pa malo počakaj.« Ko so medvedje odšli, je učitelj obstal pred Pikijem. »Kot sem rekel,« je začel, »mačke mijavkajo. Vendar pa se zgodi, da ta ali ona včasih tudi zažvižga, Ampak naj to ostane med nama.«
> 434	18	48	600	pokima	oseba: Piki -[pokima]-> predmet: zadeva	Piki je pokimal in s tem je bila zadeva v medvedji šoli opravljena. Jaz pa sem se moral sosedu opravičiti in mu kupiti novega kanarčka. Zdaj premišljujem, ali ne bi še našemu mačku kupil nagobčnika. Piki igra šah Učitelj je rekel Pikiju: »Se greva šah?« Piki je kot ubogljiv medved pokimal. Postavila sta ﬁgure in učitelj je rekel: »Če se boš naučil dobro igrati, boš postal še medvedji šahovski velemojster.« Piki je spet pokimal.
> 435	20	535	48	govori	oseba: učitelj -[govori]-> oseba: Piki	Učitelj je postal živčen: »Kaj pa toliko premišljuješ, požri kmeta, pa konec.« Piki se je malo obotavljal, potem pa vprašal: »Misliš resno?« »Seveda,« je rekel učitelj. »No, daj že.« Piki je s tresočo se taco vzel belega kmeta in postavil črnega na njegovo polje. Učitelj se je zagledal v šahovnico, Piki pa je pogledal kmeta, ki ga je držal v taci, potem pa skomignil z rameni in ga po tihem požrl.
> 436	21	535	647	igra	oseba: učitelj -[igra]-> igra: šah	Učitelj ni nič opazil in tako sta igrala naprej. Začela sta ne veliko zamenjevati ﬁgure in Piki je vsako, ki jo je pobral z deske, najprej malo pogledal z leve in desne, potem pa jo je požrl. Polagoma sta se bližala koncu igre. Kljub temu, da je Piki na veliko jedel učiteljeve ﬁgure, je bil učitelj spretnejši in tako je Pikiju kmalu ostal samo še kralj s trdnjavama, učitelj pa je imel ob kralju in trdnjavah še kraljico.
> 437	21	48	195	ima	oseba: Piki -[ima]-> predmet: kralj	Učitelj ni nič opazil in tako sta igrala naprej. Začela sta ne veliko zamenjevati ﬁgure in Piki je vsako, ki jo je pobral z deske, najprej malo pogledal z leve in desne, potem pa jo je požrl. Polagoma sta se bližala koncu igre. Kljub temu, da je Piki na veliko jedel učiteljeve ﬁgure, je bil učitelj spretnejši in tako je Pikiju kmalu ostal samo še kralj s trdnjavama, učitelj pa je imel ob kralju in trdnjavah še kraljico.
> 438	22	535	647	napoveda	oseba: učitelj -[napoveda]-> igra: šah	»Zdaj te bom pa matiral,« je rekel učitelj in napovedal šah. Pikijev črni kralj je begal sem in tja po deski in zašel na nevarni rob. Za silo ga je še branila ena izmed trdnjav, in ko je Piki prišel na potezo, se je spet globoko zamislil. »Kaj pa spet mečkaš,« je rekel učitelj. »Saj ti tako nič ne pomaga, matiral te bom in to takoj.« Tedaj se je Piki odločil.
> 439	22	57	114	beži	predmet: Pikijev kralj -[beži]-> predmet: deska	»Zdaj te bom pa matiral,« je rekel učitelj in napovedal šah. Pikijev črni kralj je begal sem in tja po deski in zašel na nevarni rob. Za silo ga je še branila ena izmed trdnjav, in ko je Piki prišel na potezo, se je spet globoko zamislil. »Kaj pa spet mečkaš,« je rekel učitelj. »Saj ti tako nič ne pomaga, matiral te bom in to takoj.« Tedaj se je Piki odločil.
> 440	22	48	385	zamisli se	oseba: Piki -[zamisli se]-> predmet: poteza	»Zdaj te bom pa matiral,« je rekel učitelj in napovedal šah. Pikijev črni kralj je begal sem in tja po deski in zašel na nevarni rob. Za silo ga je še branila ena izmed trdnjav, in ko je Piki prišel na potezo, se je spet globoko zamislil. »Kaj pa spet mečkaš,« je rekel učitelj. »Saj ti tako nič ne pomaga, matiral te bom in to takoj.« Tedaj se je Piki odločil.
> 441	22	535	48	opozori	oseba: učitelj -[opozori]-> oseba: Piki	»Zdaj te bom pa matiral,« je rekel učitelj in napovedal šah. Pikijev črni kralj je begal sem in tja po deski in zašel na nevarni rob. Za silo ga je še branila ena izmed trdnjav, in ko je Piki prišel na potezo, se je spet globoko zamislil. »Kaj pa spet mečkaš,« je rekel učitelj. »Saj ti tako nič ne pomaga, matiral te bom in to takoj.« Tedaj se je Piki odločil.
> 442	25	48	535	govori	oseba: Piki -[govori]-> oseba: učitelj	« Šele zdaj je učitelj razumel za kaj gre. Belih ﬁgur, ki jih je Piki pobral, ni bilo nikjer. »Zakaj si jih pa požrl?« je vprašal učitelj. »Saj si mi vendar sam rekel, naj požrem kmeta, potem pa sem požrl še druge,« je rekel Piki. »Kaj bova pa zdaj?« je rekel učitelj. »Kako pa naj zdaj šahirava?« Piki je rekel: »Prosi očka, naj ti kupi nov šah.
> 443	26	535	48	popravi	oseba: učitelj -[popravi]-> oseba: Piki	« In potem sta oba prišla k meni. Medvedja mamica Nekega večera, ko sta ležala v postelji in si kakor ponavadi pripovedovala zgodbe, je učitelj vprašal Pikija: »Ali veš kako si prišel na svet?« »Vem,« je odgovoril Piki. »Naredila me je medvedja mamica.« »Ne reče se 'naredila' ampak 'rodila', če kaj vem,« je rekel učitelj. »Že mogoče,« je odgovoril Piki, »ampak mene je zagotovo naredila. Pa ne samo mene.
> 444	26	48	535	odgovarja	oseba: Piki -[odgovarja]-> oseba: učitelj	« In potem sta oba prišla k meni. Medvedja mamica Nekega večera, ko sta ležala v postelji in si kakor ponavadi pripovedovala zgodbe, je učitelj vprašal Pikija: »Ali veš kako si prišel na svet?« »Vem,« je odgovoril Piki. »Naredila me je medvedja mamica.« »Ne reče se 'naredila' ampak 'rodila', če kaj vem,« je rekel učitelj. »Že mogoče,« je odgovoril Piki, »ampak mene je zagotovo naredila. Pa ne samo mene.
> 445	27	244	264	proizvaja	oseba: medvedja mamica -[proizvaja]-> predmet: medvedki	Tudi vse druge medvedke.« »Medvedja mamica, praviš?« se je čudil učitelj. »Prvič slišim. Povej mi kaj o njej.« »Medvedja mamica je šivilja, ki šiva medvedke,« je rekel Piki. »Vsak dan naredi enega in jih dela cel mesec, tako da sedi na koncu meseca na polici trideset medvedkov. Saj ima mesec trideset dni, kajne?« »Ne vsak,« je rekel učitelj. »Sicer pa ni važno,« je rekel Piki.
> 446	27	535	48	popravi	oseba: učitelj -[popravi]-> oseba: Piki	Tudi vse druge medvedke.« »Medvedja mamica, praviš?« se je čudil učitelj. »Prvič slišim. Povej mi kaj o njej.« »Medvedja mamica je šivilja, ki šiva medvedke,« je rekel Piki. »Vsak dan naredi enega in jih dela cel mesec, tako da sedi na koncu meseca na polici trideset medvedkov. Saj ima mesec trideset dni, kajne?« »Ne vsak,« je rekel učitelj. »Sicer pa ni važno,« je rekel Piki.
> 447	28	48	450	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: rvav in bel pliš	»Ko sem bil jaz na vrsti, nas je bilo pač trideset. Je že bil tak mesec. Prav dobro vem, da nas je bilo trideset, ker je mene naredila prvega in sem imel čas šteti. Imela je krojne pole za velike in srednje in majhne medvedke. Zame je izbrala posebno lep kroj. Razen tega mi je prišila rjav in bel pliš. Takega kožuha nima vsak medvedek. Po večini so rumeni, kot da bi bili levi in ne medvedi. Si že kdaj videl rjavega leva?«
> 448	30	244	280	ima material	oseba: medvedja mamica -[ima material]-> material: morska trava	Švrk, švrk, švrk -telo, švrk, švrk -roke, švrk, švrk -noge, pa še švrc. Švrc -ušesa in kožuh je bil pripravljen. Potem je v podlogo nabasala vato ali morsko travo, prišila nanjo kožuh, pripela k telesu noge, roke in glavo, na glavo pa še smrček, ušesa in oči. Ta ali oni medvedek je dobil tudi pentljo okrog vratu. Ko je bil sešit, si ga je medvedja mamica še enkrat skrbno ogledala, ga pokrtačila in postavila na polico.
> 449	85	19	323	se smeji	oseba: Jupiter -[se smeji]-> predmet: ogledala	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 450	85	672	346	se izgubi	predmet: železnica -[se izgubi]-> prostor: paviljon s skrivnostnim napisom	Od tam sta šla v paviljon z ogledali, kjer sta se od srca nasmejala. Skoz prvo ogledalo sta se valila kot sodčka, v drugem sta shujšala kot zobotrebca, v tretjem sta imela glavi kot hruški, v četrtem pa čeljusti kot ljudožerca. Potem sta si šla ogledat železnico. Tekla je skoz predore pod mizo, mimo lepega ribnika, po katerem so plavale ladjice, ter se naposled zgubila v paviljonu s skrivnostnim napisom HIŠA STRAHOV. »Si greva ogledat strahove?« je vprašal Piki.
> 451	87	48	302	čuti	oseba: Piki -[čuti]-> predmet: nekaj	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 452	87	48	19	se smeji	oseba: Piki -[se smeji]-> oseba: Jupiter	V temi sta Piki in Jupiter začutila, da ju je nekaj mehko pobožalo po obrazu, v naslednjem trenutku pa sta bila že na prostem. »Smrt me je povohala,« se je ponorčeval Josip Jupiter. »Mene tudi,« se je zarežal Piki. »Prav poščegetala me je pod nosom. Najraje bi jo zagrabil za rep.« »Ne vem zagotovo,« je rekel Piki, »a lahko se prepričava.« Zarežala sta se in se drugič podala v nevarni predor.
> 453	89	18	296	ima lastnost	oseba: Josip Jupiter -[ima lastnost]-> značilnost: navdušen	Žal je v temi slabo preračunala smer in padla naravnost v stari lavor, ki ga je učitelj spremenil v ribnik. Nastala je strašna povodenj, smrt pa je iz lavorja v podobi mokrega mačka jadrno švignila na balkon. Piki in Josip Jupiter sta se imenitno zabavala. Vsakemu, ki ju je hotel poslušati, sta pripovedovala, da sta držala smrt že za rep in je le malo manjkalo, pa bi jo stlačila v vrečo. Zatrjevala sta, da tako sijajnega novoletnega sejma še ni bilo. Manj navdušenja pa je kazal učitelj.
> 454	90	535	271	zapisuje	oseba: učitelj -[zapisuje]-> dejanje: minus v vedenju	Bil je strašno jezen na smrt, ki je padla v ribnik, zaradi česar je moral tri ure drgniti parket v dnevni sobi. Spominske knjige Na lepem so vsi medvedje imeli spominske knjige. Pri pouku je kar naprej nekaj šumelo in krožilo pod klopmi. Ko je učitelj pri računstvu vprašal Benjamina: »Koliko je ena in ena?« je ta odgovoril: »Ena in ena je dve-nikar ne pozabi na me!« »Ne bom,« je rekel učitelj in mu zapisal velik minus v vedenju.
> 455	91	535	15	preveril	oseba: učitelj -[preveril]-> predmet: Flokijeva knjiga	Potem je nabral po razredu osem spominskih knjig in jih zadržal za nedoločen čas. Medtem ko so poparjeni otroci prepisovali s table stavek »Med poukom mora biti spominska knjiga v torbi«, je učitelj sedel za mizo in listal po zaplenjenem blagu. Najprej mu je prišla pod roke Flokijeva knjiga. V njej je bil en sam zapis. Poleg lepo pobarvanega medveda so stale vrstice: Lep in mlad je na tej sliki tvoj prijatelj medved Piki tudi ko bo grd in star, ne pozabi ga nikdar.
> 456	93	491	94	nariše	oseba: stari Marko -[nariše]-> risba: barko	Za spomin narišem barko se podpišem stari Marko. Učitelj je požrl slino in listal naprej. Knjiga je bila polna nageljnov, vrtnic in pravljičnih hišic. Pod eno izmed njih je pisalo: Tukaj hišica stoji, v hiši deklica živi, ko na okno se nasloni, se ji Benjamin prikloni. na naslednji strani je bila v tiskanih črkah ovekovečena modrost Marka Prvega: Timika,mladost je vsaka kakor mehka, gosta dlaka, a medvedu kakor muli kožuh kmalu se oguli. »Kaj takega,« je pomislil učitelj.
> 457	93	187	292	vsebuje	predmet: knjiga -[vsebuje]-> vsebina: nageljnov	Za spomin narišem barko se podpišem stari Marko. Učitelj je požrl slino in listal naprej. Knjiga je bila polna nageljnov, vrtnic in pravljičnih hišic. Pod eno izmed njih je pisalo: Tukaj hišica stoji, v hiši deklica živi, ko na okno se nasloni, se ji Benjamin prikloni. na naslednji strani je bila v tiskanih črkah ovekovečena modrost Marka Prvega: Timika,mladost je vsaka kakor mehka, gosta dlaka, a medvedu kakor muli kožuh kmalu se oguli. »Kaj takega,« je pomislil učitelj.
> 458	94	58	554	vsebuje	predmet: Pikijeva knjižica -[vsebuje]-> vsebina: verze	Sledilo je nekaj praznih listov, potem pa sta bili čez celo stran narisani dve Timiki, ena objokana in ena nasmejana. Spodaj je stalo kratko in jedrnato: Bodi v sreči, bodi v sili zmeraj nate misli Filip. Medvedje so že desetič pisali »Med poukom mora biti spominska knjiga v torbi«, učitelj pa je začel prebirati Pikijevo knjižico. Pod veliko srebrno raketo je našel verze: Lunibus leti na Luno Piki je njegov šofer. Potnike ima na skrbi zvesti Josip Jupiter.
> 459	94	18	468	ima poklic	oseba: Josip Jupiter -[ima poklic]-> poklic: skrbnik potnikov	Sledilo je nekaj praznih listov, potem pa sta bili čez celo stran narisani dve Timiki, ena objokana in ena nasmejana. Spodaj je stalo kratko in jedrnato: Bodi v sreči, bodi v sili zmeraj nate misli Filip. Medvedje so že desetič pisali »Med poukom mora biti spominska knjiga v torbi«, učitelj pa je začel prebirati Pikijevo knjižico. Pod veliko srebrno raketo je našel verze: Lunibus leti na Luno Piki je njegov šofer. Potnike ima na skrbi zvesti Josip Jupiter.
> 460	96	535	249	obljubljajo	oseba: učitelj -[obljubljajo]-> skupina: medvedje	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 461	96	535	436	odhaja	oseba: učitelj -[odhaja]-> prostor: razred	»Mir,« je rekel učitelj. »Bom še premislil. Če jih boste imeli med poukom v torbi, potem mogoče.« »Bomo, bomo,« so zaklicali medvedje. »Mogoče,« je ponovil učitelj in odšel iz razreda. Zdaj so te spominske knjige pri meni. Učitelj je rekel, da bi njemu vzelo pisanje preveč časa, jaz pa da bom stresel verze kar iz rokava. Ampak čeprav že ves popoldan tresem rokave, ni iz njih še nič priletelo.
> 462	98	254	637	ima opremo	skupina: medvedji gasilci -[ima opremo]-> predmet: čelade, vrv, gasilske sekirice	Šel sem pogledat, kaj se dogaja, in učitelj mi je povedal, da so pravkar ustanovili medvedjo gasilsko četo. Povabil me je, naj bom navzoč pri prvi vaji, češ da bo to spodbudno za mlade gasilce. Ti so na znamenje trobentača Pikija že tekli od vseh strani in se, kot bi trenil, postavili v vrsto. Vsak je imel na glavi čelado, za pasom vrv, ob boku pa gasilsko sekirico.
> 463	99	48	583	poravnava	oseba: Piki -[poravnava]-> skupina: vrsto	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 464	99	535	254	pozdravi	oseba: učitelj -[pozdravi]-> skupina: medvedji gasilci	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 465	99	254	331	uporabljajo	skupina: medvedji gasilci -[uporabljajo]-> predmet: oprema	Piki je vrsto poravnal, potem pa s strumnim korakom stopil pred učitelja: »Tovariš poveljnik, medvedja gasilska četa je pripravljena za vajo.« Poveljnik je vstal in rekel: »Zdravo, tovariši gasilci.« Medvedje so v zboru odgovorili: »Zdravo, tovariš poveljnik.« Potem so začeli z vajami. V popolni opremi so morali teči na kratke proge, preskakovati ovire, odvijati in zvijati cevi, postavljati in podirati lestve ter z višine skakati na razpete ponjave.
> 466	100	527	136	kliče	predmet: trobenta -[kliče]-> skupina: gasilce	Bili so zelo požrtvovalni in zato sem jih po končani vaji s poveljnikom vred povabil na malinovec. Poslej je trobenta vsak dan po kosilu klicala gasilce »na pomoč«. Četa je kmalu obvlada tudi motorizacij in zvokom trobente so se pridružili zvoki gasilske sirene in cviljenje gum gasilskega avta, ki ga je višji gasilec Piki vozil na »kraj požara«.
> 467	101	638	142	prireja	skupina: četa -[prireja]-> dogodek: gasilski miting	Poveljnik je rekel, da bi četi zelo koristile »vroče vaje«, to se pravi, gašenje »požara« v peči dnevne sobe, vendar mu tega kot višji gasilski inšpektor nisem mogel dovoliti. Približala se je pomlad. Nehali smo kuriti peči in nevarnost požarov se je zmanjšala skoraj na ničlo. A poveljnik je menil, da je treba znanje preizkusiti, in tako je četa v kopalnici priredila gasilski miting pod nazivom POŽAR V NBOTIČNIKU. Prepričal sem se, da je moštvo odlično izurjeno.
> 468	102	141	194	odhiti	avto: gasilski avto -[odhiti]-> prostor: kraj požara	Trobent je komaj dobro utihnila, ko je že pridrvel izza ovinka gasilski avto in s presunljivim »goo-rii, goo-rii« odhitel na kraj požara. Vrstila so se povelja: »Sestavite lestve! Razvijte cevi! Priključite vodo!« Za nebotičnik je služil veliki vodogrelec v kotu kopalnice. Lestve so se pognale do vrhnjih nadstropij, po njih sta splezala Filip in Benjamin ter začela reševati »ogrožene prebivalce«.
> 469	102	210	577	se pognajo	predmet: lestve -[se pognajo]-> prostor: vrhnja nadstropja	Trobent je komaj dobro utihnila, ko je že pridrvel izza ovinka gasilski avto in s presunljivim »goo-rii, goo-rii« odhitel na kraj požara. Vrstila so se povelja: »Sestavite lestve! Razvijte cevi! Priključite vodo!« Za nebotičnik je služil veliki vodogrelec v kotu kopalnice. Lestve so se pognale do vrhnjih nadstropij, po njih sta splezala Filip in Benjamin ter začela reševati »ogrožene prebivalce«.
> 470	103	48	104	uporabi	oseba: Piki -[uporabi]-> predmet: cev	Metala sta jih v globino, kjer so jih štirje gasilci spretno lovili v ponjavo, Medtem je višji gasilec Piki pripravil motorno brizgalno. Na vodovodno pipo je nataknil dolgo cev ter z roba umivalnika usmeril močan curek proti »plamenom«. Žal mu je na mokrih tleh spodrsnil in je padel, vendar pa cevi tudi med padcem ni izpustil iz rok. Po nesreči je curek zadel reševalca Benjamina in Filipa, ki sta iz vrtoglave višine strmoglavila na ponjavo, s katere se je samo trenutek prej pobral Piki.
> 471	103	3	377	padeta	skupina: Benjamin in Filip -[padeta]-> prostor: ponjavo	Metala sta jih v globino, kjer so jih štirje gasilci spretno lovili v ponjavo, Medtem je višji gasilec Piki pripravil motorno brizgalno. Na vodovodno pipo je nataknil dolgo cev ter z roba umivalnika usmeril močan curek proti »plamenom«. Žal mu je na mokrih tleh spodrsnil in je padel, vendar pa cevi tudi med padcem ni izpustil iz rok. Po nesreči je curek zadel reševalca Benjamina in Filipa, ki sta iz vrtoglave višine strmoglavila na ponjavo, s katere se je samo trenutek prej pobral Piki.
> 472	104	137	396	postanejo	skupina: gasilci -[postanejo]-> značilnost: pravi gasilci	S cevjo, iz katere je še zmeraj bruhala voda, je »pogasil« tudi nekaj na tleh stoječih gasilcev. Zdaj so si vsi otepali mokre kožuhe in nič kaj prijazno gledali Pikija. Ker rokoborba ni bila na sporedu gasilskega mitinga, je poveljnik brž izključil motorno brizgalno ter razglasil, da je požar pogašen in stanovalci rešeni. Gasilci so pospravili svojo opremo, Piki je zatrobental in odpeljali so se domov. Na kratki slovesnosti pred gasilskim domom je učitelj povedal, da so danes doživeli ognjeni krst in postali pravi gasilci.
> 473	107	535	303	vzdihne	oseba: učitelj -[vzdihne]-> značilnost: nesposobnost zaspati	Sklenili so, da bodo čebulice posadili v soboto dopoldne, ko bodo prosti in ne bodo imeli drugih skrbi. Tisto noč je bilo zadušljivo, tako da učitelj in Piki dolgo nista mogla zaspati. Dvakrat sta šla pit slatino, pa ni nič pomagalo. Ko smo vsi drugi že spali, sta se še zmeraj premetavala po postelji. »Ne morem in ne morem zaspati,« je vzdihnil učitelj. »Jaz tudi ne,« je zamomljal Piki in si obrisal potno čelo.
> 474	31	535	48	odgovarja	oseba: učitelj -[odgovarja]-> oseba: Piki	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 475	31	48	244	trdi	oseba: Piki -[trdi]-> oseba: medvedja mamica	Imela nas je rada in se je z nami pogovarjala. Jaz sem bil dolgo pri njej, nekateri medvedki pa samo po dan ali dva.« »Kako pa to?« je vprašal učitelj. »Ali so ušli?« »Sem ti jaz že kdaj ušel?« je užaljeno vprašal Piki. »Nisi,« je rekel učitelj. »Tudi medvedji mamici ni nobeden ušel,« je nadaljeval Piki.
> 476	32	525	264	dela	prostor: trgovina -[dela]-> predmet: medvedki	»Ampak, ko se nas je nabralo trideset, je prišel možakar z velikim usnjenim kovčkom in medvedja mamica nas je dala njemu. Zložil nas je v kovček in odnesel v trgovino. Tam so nam dali okrog vratu listke i n na listkih je pisalo, koliko stanemo. Potem smo sedeli v izložbi, nekateri pa na policah. Jaz sem sedel v izložbi in ko je prišel mimo tvoj očka, sem mu pomežiknil, pa je stopil v trgovino in me kupil Tako sem prišel k tebi.«
> 477	34	48	535	živi z	oseba: Piki -[živi z]-> oseba: učitelj	Učitelj se je malo zamislil, potem je skomignil z rameni:»Piši kakšnemu Žužuju.« Piki je vneto pokimal, sedel za mizo in pri priči začel pisati z velikimi tiskanimi črkami: »Dragi Žužu številka 2, napisal ti bom pismo. Jaz sem Žužu številka 1. Gotovo se me še spomniš, saj sva na polici pri medvedji mamici sedela drug ob drugem. Zdaj se imenujem Piki in stanujem pri učitelju v Ljubljani.
> 478	35	50	259	ima prijatelje	oseba: Piki Jakob -[ima prijatelje]-> oseba: medvedji prijatelji	Če ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.
> 479	36	48	35	piše	oseba: Piki -[piše]-> oseba: Medolizis	Piki je nato pisal še medvedu Tediju v Holandijo, medvedu Marmeladovu v Rusijo, medvedu Berensonu na Švedsko, medvedu Medolizisu v Grčijo in medvedu Mečkoviču v Beograd. Na odgovore mu ni bilo treba dolgo čakati, prvo pa je prišlo Žužujevo pismo. Žužu je pisal: »Dragi moj Piki, z medvedi v Parizu je vse v redu. Jedo med, hodijo v šolo in se vozijo z metrojem. Tudi jaz se rad vozim z metrojem. Če še ne veš, se tako imenuje podzemna železnica.
> 480	38	394	50	išče	oseba: poštar -[išče]-> oseba: Piki Jakob	Osemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.
> 481	39	535	625	ima zobobol	oseba: učitelj -[ima zobobol]-> značilnost: zobobol	Seveda pa moram povedati, da sta učitelj in Piki napisala podnajemnik le zato, da se bolj imenitno sliši. V resnici je Piki član naše družine in mu za stanovanje ni treba čisto nič plačati. Pri zobozdravniku Pikija je bolel zob in zato smo sklenili, da pojdemo k zobozdravniku. Resda je bolel zob tudi učitelja in tudi mene je cukalo po čeljustih, vendar je bil Piki največji revež. Vso noč se je premetaval po postelji in nič ni pomagalo, da smo mu dajali tople in mrzle obkladke.
> 482	41	535	48	svetuje	oseba: učitelj -[svetuje]-> oseba: Piki	»Se-seveda,« je zajecljal Piki. »Pri zobozdravniku vsak pravi medved stisne zobe in malo potrpi,« je končal učitelj. »Se-se-seveda,« je prikimal Piki. Ko smo vstopili v čakalnico, je bilo tam že nekaj otrok, medveda pa prav nobenega. Otroci so začudeno gledali obvezanega Pikija, dokler ni učitelj enega vprašal, ali misli, da medveda ne morejo boleti zobje.
> 483	42	102	50	kliče	oseba: bolniška sestra -[kliče]-> oseba: Piki Jakob	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 484	42	50	610	obiskuje	oseba: Piki Jakob -[obiskuje]-> oseba: zdravnik	To je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.
> 485	43	610	48	zdravi	oseba: zdravnik -[zdravi]-> oseba: Piki	»Bomo že pokazali temu nesramnežu,« je rekel zdravnik. Piki je sedel na stol in odprl gobček. Zdravnik je s kovinsko paličico trkal po zobeh in spraševal: »Ali je ta? Ali je ta?« Piki je odgovarjal nekje iz trebuha: »Nhe, nhe.« Potem sta naletela na pravega, Ko je zdravnik potrkal po njem, je Piki javknil: »Auvh.«
> 486	45	535	626	obiskuje	oseba: učitelj -[obiskuje]-> oseba: zobozdravnik	Potem je junaško odprl gobec, pošteno zamižal in preden bi naštel do tri, je bil zob zunaj. Za Pikijem je bil na vrsti učitelj. Njegov zob je bil manj načet kakor Pikijev, zato ga je zobozdravnik samo plombiral. Učitelj se je malo spotil, vendar ni niti enkrat zastokal in tudi ni ugriznil zobozdravnika. Na koncu je hotel zdravnik pregledati še mene, a me v tistem hipu zobje niso niti najmanj boleli in zato sem rekel, da bom prišel raje drugič. Potem smo zadovoljni odšli.
> 487	50	251	593	srečajo	oseba: medvedji -[srečajo]-> značilnost: vzpon	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 488	50	48	576	prileze	oseba: Piki -[prileze]-> prostor: vrh	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 489	50	48	151	teče	oseba: Piki -[teče]-> prostor: greben	Drugi so se pognali, kar so jih nesle pete, naprej proti južnemu gričevju ali po domače spalnici. Tukaj jih je čakal precej hud vzpon na stari grad ali po domače omaro in dolgo je trajalo, preden je Piki kot prvi prilezel na vrh. Ko je tekel po grebenu skozi temno goščavo ali po domače skoz razmetane učiteljeve igrače, je v goščavi nekaj zašumelo in se spustilo po drugem pobočju navzdol. Medtem je tudi Piki pretekel greben in se v skoku pognal na mehki travnik ali po domače na posteljo.
> 490	51	48	266	drvi	oseba: Piki -[drvi]-> prostor: mehki travnik	A še preden se je dobro ujel, se je mehki travnik premaknil in s Pikijem vred oddrvel, da se je kar kadilo za njima. Piki se ga je krčevito oklenil in kmalu spoznal, da to ni leteči travnik, ampak hudi tiger ali po domače naš maček. Medvedji športniki so ga vrgli iz prijetnega dremeža in zelo se je prestrašil, ko je začutil, da ga je na lepem nekdo zajahal.
> 491	53	48	616	prejme	oseba: Piki -[prejme]-> predmet: zlato medaljo	Ko je Piki stopil na zmagovalni oder in prejel iz učiteljevih rok zlato medaljo in velikansko hruško, so tekmovalci zaploskali, vendar so nekateri godrnjali, da ta zmaga ni čisto po pravilih. Učitelj pa je reke, da je vse v redu, ker Piki ni jezdil tigra nalašč, ampak po sili. Potem je Piki razrezal hruško in jo pravično razdelil. Zdaj so bili vsi zadovoljni. Le jezni tiger si je šel brusit kremplje ob podrti hrast.
> 492	54	247	454	so	oseba: medvedje -[so]-> značilnost: sami doma	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 493	54	48	595	sedel	oseba: Piki -[sedel]-> prostor: zaboj za igrače	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 494	54	48	70	pogovarja	oseba: Piki -[pogovarja]-> oseba: Stari Marko	Od takrat nimamo več ﬁkusa Piki ima vročino Bil je vroč poletni dan in medvedje so bili sami doma. Učitelj, njegova mama in sestra ter jaz smo se odpeljali kopat na Soro. Piki je sedel v zaboju za igrače in se potil. Premišljeval je, kaj naj stori, da bi se ohladil. Presedel se je na polico, pa ni nič pomagalo. Tedaj je zagledal Starega Marka, ki je ležal pod klopjo. Piki je rekel: »Strašno mi je vroče.«
> 495	56	48	367	uporablja	oseba: Piki -[uporablja]-> predmet: pokrovko	Mene pa pusti pri miru, ker bi rad spal.« Stari Marko se je obrnil v kot in zadremal, Piki pa si je obrisal potno čelo in počasi splezal s police. Zlezel je v zaboj za igrače in komaj izvlekel majhen štedilnik, lonček za čaj in pokrovko. Ko je čakal, da voda zavre, se je spomnil na tableto. Previdno je splezal do stenske lekarnice in jo odprl. Na poličkah je stalo mnogo škatlic in na vsaki je bil drugačen napis.
> 496	57	81	580	zdravi	zdravilo: aspirin -[zdravi]-> bolezen: vročina	Piki ni vedel, za katero naj se odloči. Poklical je Starega Marka. »Kaj že spet hočeš?« »Katero tableto pa naj vzamem?« je vprašal Piki. »Aspirin vendar,« je rekel Stari Marko, »to bi že lahko vedel.« »Saj nisem zdravnik,« je rekel Piki. »Zakaj pa zdravnik,« je zamomljal Stari Marko. »Če te kaj speče, rečeš 'as'. Če imaš torej vročino, moraš vzeti as-pirin, razumeš?«
> 497	58	48	470	ima lastnost	oseba: Piki -[ima lastnost]-> značilnost: slabost	»Aha,« je rekel Piki, čeprav ni čisto dobro razumel. Ker pa mu je bilo zelo vroče, je pojedel kar dva aspirina in spil dve skodelici vročega lipovega čaja. Čez pet minut se je začel tako potiti, da je vse teklo od njega, in zdelo se mu je, da bo vsak hip omedlel. Tedaj se je vrnil učitelj in začudeno vprašal: »Kaj pa je s tabo, Piki?« »Sla-slabo mi je,« je zajavkal Piki.
> 498	59	48	535	se pogovarja	oseba: Piki -[se pogovarja]-> oseba: učitelj	»Hu-hudo vročino imam.« »Takoj bomo videli,« je rekel učitelj in prinesel toplomer. Vtaknil ga je medvedku pod pazduho in ko je čez pet minut pogledal na številčnico, se je zasmejal«36,5 imaš, Piki, to ni nobena vročina.« »Pa mi je takooo vroooče,« je zajamral Piki. »Seveda,« je rekel učitelj. »Danes je bil zelo vroč dan. 30 stopinj v senci.« »Vidiš,« je rekel Piki.
> 499	63	535	150	zahteva	oseba: učitelj -[zahteva]-> oseba: govorec	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 500	63	150	226	odloča	oseba: govorec -[odloča]-> žival: maček	Ampak učiteljevim zahtevam še zmeraj ni bilo konca. Komaj sem popustil zaradi medvedov, že mi je rekel, da bi morali vzeti s seboj tudi našega mačka. Odločno sem se uprl. Učitelj me je pogledal: »Si že pozabil, kako je bilo lani?« »Ne,« sem odgovoril, »dobro vem, da je padel v katran in da smo ga potem teden dni prali v terpentinu. Zaradi mene pa lahko skoči tudi v goreči špirit, če je tako trapast, ampak na morje ne bo šel.
> 501	64	48	349	vzame	oseba: Piki -[vzame]-> predmet: perilo	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 502	64	48	170	vzame	oseba: Piki -[vzame]-> plovilo: jadrnica	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 503	64	48	279	obleče	oseba: Piki -[obleče]-> oblačila: mornarska majica	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 504	64	150	535	dodaja	oseba: govorec -[dodaja]-> oseba: učitelj	Pri priči ga boš odnesel k sosedovim.« Medtem ko sva midva razpravljala, je Piki polnil svoj kovček. Vanj je zložil perilo, sandale, plavalni obroč, majhno jadrnico, balinčke in novo, svetlo zeleno ščetko. Potem si je oblekel mornarsko majico, si nataknil dolge snežno bele hlače in se pokril s kapitansko kapo. »Manjkata ti samo še lesena noga in črn trak čez oko, pa bi bil pravi gusar,« je rekel učitelj. »Kaj pa pipa?« sem rekel.
> 505	65	535	150	svetuje	oseba: učitelj -[svetuje]-> oseba: govorec	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 506	65	48	370	prejema	oseba: Piki -[prejema]-> gesta: poljubček	»Pametni gusarji ne kadijo,« je rekel učitelj s poudarkom, »ker vejo, da je tobak škodljiv.« »Res je,« sem zamomljal in potlačil cigarete globoko v žep. Naslednje jutro smo sedli v avto in se odpeljali. Če štejem tudi medvede, nas je bilo kar precej, vendar se nismo stiskali. Kapitan Piki je sedel na sprednjem sedežu pri učiteljevi mami in po vojaško pozdravljal nasproti vozeče avtomobile. Vozniki so mu odzdravljali in neka opica mu je celo vrgla poljubček. Pripeljali smo se na morje.
> 507	66	48	433	piše	oseba: Piki -[piše]-> dokument: razglednica	Piki je bil zelo zadovoljen. Z učiteljem sta lovila ribe. Resda nista nobene ujela, ampak to ni važno. To še pride. Veselili smo se sonca, slane vode in sladoleda ter napisali kup razglednic. Eno, dragi bralci, smo poslali tudi vam. Ko jo boste prejeli, boste videli, da se je v desni spodnji kot razločno podpisal VAŠ PIKI. Piki v vozniški šoli Vožnja na morje je bila Pikiju zelo všeč. Seveda so ga med potjo močno zanimale tudi moje šoferske umetnije.
> 508	68	48	88	vozi	oseba: Piki -[vozi]-> predmet: avtomobilček	Piki jih je risal v velik zvezek, ki ga je ponoči polagal pod blazino. Rekel je, da tako o njih tudi sanja in si jih laže zapomni. Tudi druga pravila mu niso delala preglavic. Ko je pri predsednici Rdečega križa, učiteljevi starejši sestri, z odliko opravil še tečaj prve pomoči, sva začela z vožnjami. Učitelj nama je posodil enega izmed svojih slabše ohranjenih avtomobilčkov. Piki je momljal, da je to »stara škatla«.
> 509	71	48	519	zagledal se	oseba: Piki -[zagledal se]-> predmet: tovornjak	»bom tudi jaz prižgal dolge.« Komaj sem ga prepričal, da se na cesti ne sme ravnati po pravilu »zob za zob«. Medtem sva se počasi približevala tovornjaku. Kmalu sva ugotovila, da se sploh ne premika. »Mogoče ima okvaro,« sem rekel. Piki se je nagnil naprej in se zagledal proti tovornjaku. Potem je rekel: »Nima okvare.« »Kar tako na daleč pa tega ne moreš vedeti,« sem ugovarjal.
> 510	73	48	82	vozil	oseba: Piki -[vozil]-> predmet: avto	Tako so tekle vozniške ure in čez mesec dni je bil Piki že tako izurjen, da se je lahko priglasil k izpitu. Predsednik izpitne komisije je bil učitelj. Mrko je sedel na zadnjem sedežu in zapisoval kazenske točke. Pikiju je avto štirikrat ugasnil ali, kakor pravijo šoferji »crknil«, vendar ga je zmeraj spet uspešno pognal. Prvič je slabo parkiral in dvakrat je pozabil pogledati v vzvratno ogledalo. Tudi pri ritenski vožnji je bilo nekaj težav. Na koncu je predsednik seštel kazenske točke.
> 511	74	48	571	dobil	oseba: Piki -[dobil]-> dokument: vozniško dovoljenje	Od 400 dovoljenih jih je Piki nabral sam 190. Komisija, v kateri sta bili še učiteljeva mama in sestra, je razglasila, da je Piki Jakob uspešno opravil izpit. Piki je dobil vozniško dovoljenje. V njem je bilo zapisano, da sme upravljati vsa motorna vozila, namenjena za prevoz medvedov. Vsi smo mu prisrčno čestitali, Piki pa nas je pogostil s steklenico ribezovega soka. Piki voznik avtobusa Učitelj je kupil lep rdeč avtobus in Piki je vsako jutro odpeljal medvede v šolo.
> 512	75	18	489	bil	oseba: Josip Jupiter -[bil]-> poklic: sprevodnik	Za sprevodnika si je izbral Josipa Jupitra, ki je bil na svojo novo službo zelo ponosen. Po našem stanovanju je tako vsako jutro in vsak poldan trobil medvedji avtobus, v katerem je za volanom sedel Piki, vozne listke pa je prodajal in luknjal Josip Jupiter. Nič posebnega se ne bi zgodilo, če Piki in njegov sprevodnik ne bi ugotovila, da progi MEDVEDJI DOM-MEDVEDJA ŠOLA pravzaprav nekaj manjka, da bi bila prava avtobusna proga.
> 513	77	48	373	tožil	oseba: Piki -[tožil]-> značilnost: pomanjkanje potnikov	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 514	77	18	48	rekel	oseba: Josip Jupiter -[rekel]-> oseba: Piki	»Postajališča imava,« je tožil Piki, »potnikov pa ni.« »Tudi potniki bodo,« je rekel Josip Jupiter. »Samo potrpi.« Naslednje jutro so šolarji spet vstopili pri MEDVEDJEM DOMU in izstopili pri MEDVEDJI ŠOLI. Kazalo je, da tudi nazaj grede ne bo drugače. Toda, ko je Piki opoldne ustavil pri STAREM GOJZARJU, je sprevodnik rekel Benjaminu: »Izstopi.« »Zakaj?« je rekel Benjamin. »Jaz se peljem vendar do konca.«
> 515	78	69	32	dejstvo	oseba: Sprevodnik -[dejstvo]-> oseba: Marko Prvi	»Ti se ne pelješ do konca,« je rekel Josip Jupiter. »Tukaj je postaja in na postajah morajo potniki vstopati in izstopati. Zato boš zdaj izstopil.« »Ne bom,« je vztrajal Benjamin. »Pa boš,« je zavpil Josip Jupiter, pograbil Benjamina za ovratnik in ga vrgel skoz vrata. Medvedje so začeli godrnjati, vendar je sprevodnik, še preden so se prav ovedeli, na postaji PODPEČ zabrisal iz avtobusa Marka Prvega in Marka Drugega.
> 516	79	32	175	vrže	oseba: Marko Prvi -[vrže]-> predmet: kamen	Ko sta se pobrala, sta strašno žugala in Marko Prvi je vrgel celo kamen za avtobusom, vendar ga ni zadel, ker je Piki oddrvel z največjo brzino. Sprevodnik jima je mahal skoz zadnje okno in vpil, da peš hoja koristi zdravju. Potem se je obrnil k potnikom in naznanil: »Naslednja postaja pri MAČJI SKLEDI. Pripravite se za izstop!« »Kar ti se prippravi!« je rekel Filip. »Jaz sem sprevodnik,« je rekel Josip Jupiter.
> 517	82	24	423	zbirajo	oseba: Ljudje -[zbirajo]-> značilnost: prostovoljne prispevke	Sprevodnik je moral za tri dni v medvedji zapor, Piki pa dva meseca ne bo smel voziti avtobusa. Medvedje morajo povrniti tudi škodo. Zdaj zbirajo prostovoljne prispevke za popravilo avtobusa, Včeraj sta me obiskala Piki in sprevodnik. Dal sem jima deset dinarjev. Piki mi je obljubil, da bom imel pri njem zmeraj prosto vozovnico, sprevodnik pa, da me ne bo nikoli vrgel iz avtobusa. Hiša strahov Trdi dni pred novim letom je učitelj odprl novoletni sejem.

> Output is truncated to 256 KB.

We have finally reached the point when we can create a new property graph **SQL_PG_RAG_STORY**. As already mentioned above, this new property graph is based on two tables **GRAPH_ENTITIES_STORY** and **GRAPH_RELATIONS_STORY** that were created above.

We have finally reached the point when we can create a new property graph SQL_PG_RAG_STORY. As already mentioned above, this new property graph is based on two tables GRAPH_ENTITIES_STORY and GRAPH_RELATIONS_STORY that were created above.

```sql
-- Drop if exists (DDL approach; DBMS_GRAPH not required)
BEGIN
  BEGIN
    EXECUTE IMMEDIATE 'DROP PROPERTY GRAPH GRAPHUSER.SQL_PG_RAG_STORY';
  EXCEPTION
    WHEN OTHERS THEN
      -- Ignore errors if the graph doesn't exist or other non-fatal issues
      NULL;
  END;
END;
/
```

> PL/SQL procedure successfully completed.

```sql
-- Recreate the property graph
CREATE PROPERTY GRAPH GRAPHUSER.SQL_PG_RAG_STORY
  VERTEX TABLES (
    "GRAPHUSER"."GRAPH_ENTITIES_STORY"
      KEY ("ID")
      LABEL "ENTITY"
      PROPERTIES ("ENTITY_NAME", "ENTITY_TYPE")
  )
  EDGE TABLES (
    "GRAPHUSER"."GRAPH_RELATIONS_STORY"
      KEY ("ID")
      SOURCE KEY ("HEAD_ID") REFERENCES "GRAPH_ENTITIES_STORY"("ID")
      DESTINATION KEY ("TAIL_ID") REFERENCES "GRAPH_ENTITIES_STORY"("ID")
      LABEL "RELATION"
      PROPERTIES ("CHUNK_ID", "RELATION", "TEXT", "CHUNK_DATA")
  )
  OPTIONS (TRUSTED MODE, DISALLOW MIXED PROPERTY TYPES);
```

> Query executed successfully. Affected rows : 0

```sql
SELECT *
FROM user_property_graphs
WHERE GRAPH_NAME = 'SQL_PG_RAG_STORY';
```

> GRAPH_NAME	GRAPH_MODE	ALLOWS_MIXED_TYPES	INMEMORY
> SQL_PG_RAG_STORY	TRUSTED	NO	NO

Let's run some SQL Propery Graph queries ...

```sql
SELECT *
FROM GRAPH_TABLE(sql_pg_rag_story
    MATCH (n IS Entity)-[e is Relation]->(n2 is Entity)
    WHERE n.entity_name ='Piki Jakob'
    COLUMNS(n.entity_name as entity_name,
            n.entity_type as entity_type,
            e.relation, 
            n2.entity_name as entity_name_dest,
            n2.entity_type as entity_type_dest,
            e.text, 
            e.chunk_data
            ))
```

> {"table":"ENTITY_NAME\tENTITY_TYPE\tRELATION\tENTITY_NAME_DEST\tENTITY_TYPE_DEST\tTEXT\tCHUNK_DATA\nPiki Jakob\toseba\tživi\tLjubljana\tprostor\toseba: Piki Jakob -[živi]-> prostor: Ljubljana\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.\nPiki Jakob\toseba\tstanuje\tblok\tprostor\toseba: Piki Jakob -[stanuje]-> prostor: blok\tMoj učitelj je poiskal Ljubljano na zemljevidu. Rekel je, da je blizu morja. Da ne padeš noter, če ne znaš plavati. Jaz bi zadnjič skoraj utonil v kopalnici. Ampak nisem. Lepo te pozdravlja tvoj stari Žužu.« Ko je prišlo Žužujevo pismo, poštar še ni vedel, da stanuje v našem bloku tudi Piki. Zato je tisti dan pozvonil v našem stopnišču kar pri devetih vratih. Povsod je vprašal: »Prosim, ali stanuje tukaj tovariš Piki Jakob?«\nPiki Jakob\toseba\tima poštno skrinjico\tpoštna skrinjica\tpredmet\toseba: Piki Jakob -[ima poštno skrinjico]-> predmet: poštna skrinjica\tOsemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.\nPiki Jakob\toseba\tima težavo\tzobobol\tznačilnost\toseba: Piki Jakob -[ima težavo]-> značilnost: zobobol\tTo je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.\nPiki Jakob\toseba\tpiše\tneznani prejemnik\toseba\toseba: Piki Jakob -[piše]-> oseba: neznani prejemnik\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.\nPiki Jakob\toseba\tgovori o\tmačke\tžival\toseba: Piki Jakob -[govori o]-> žival: mačke\t»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.\nPiki Jakob\toseba\tpošlje pismo\tpošta\tprostor\toseba: Piki Jakob -[pošlje pismo]-> prostor: pošta\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.\nPiki Jakob\toseba\tprejme pismo\tpoštar\toseba\toseba: Piki Jakob -[prejme pismo]-> oseba: poštar\tOsemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.\nPiki Jakob\toseba\thodi v\tmedvedja šola\tprostor\toseba: Piki Jakob -[hodi v]-> prostor: medvedja šola\tMoj prijatelj Piki Jakob Kdo je Piki Piki ne stanuje v gozdu, ne v živalskem vrtu, ne v cirkusu, ne v trgovini. Piki stanuje v bloku, v četrtem nadstropju, na polici za igrače. Pikiju je ime Piki, čeprav ni pikast. Tako mu je pač ime. Ni namreč vsakdo belec, ki se Belec piše, in tudi vode ne pije vsakdo, ki se piše Vodopivec. Tako je tudi Pikiju ime Piki. Piki hodi v medvedjo šolo in ima učitelja, ki ni medved, ampak fantek.\nPiki Jakob\toseba\tima prijatelje\tmedvedji prijatelji\toseba\toseba: Piki Jakob -[ima prijatelje]-> oseba: medvedji prijatelji\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.\nPiki Jakob\toseba\tobiskuje\tzdravnik\toseba\toseba: Piki Jakob -[obiskuje]-> oseba: zdravnik\tTo je zaleglo in potem ni nihče več buljil v Pikija, ki je čisto tiho sedel na stolu zraven učitelja. Bolniška sestra je pobrala zdravstvene knjižice. Ko je prišla do Pikija, ga je pobožala in Piki se je hvaležno nasmehnil. Čakali smo pol ure. Potem je sestra skoz vrata zaklicala: »Piki Jakob!« Odšli smo v ordinacijo. Zdravnik je prijazno pozdravil in vprašal: »Kaj pa je s tabo, Piki?« »Zo-zo-zob me boli,« je zajecljal Piki.\nPiki Jakob\toseba\todgovarja\tučitelj\toseba\toseba: Piki Jakob -[odgovarja]-> oseba: učitelj\t»To je pes,« je odgovoril Filip. »Kako govori pes?« »Pes laja.« »Dobro. Kako pa se pogovarjajo ptički?« »Ptički gostolijo, žvrgolijo in žvižgajo,« je odgovorila Timika. »Odlično,« je rekel učitelj. »Piki Jakob, kaj veš o mačkah?« »Mačke mijavkajo in žvižgajo,« je rekel Piki. »Kaj praviš?« je rekel učitelj in strogo pogledal Pikija. »Mačke mijavkajo in žvižgajo,« je ponovil Piki.\nPiki Jakob\toseba\tima učitelja\tučitelj\toseba\toseba: Piki Jakob -[ima učitelja]-> oseba: učitelj\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto.\nPiki Jakob\toseba\tstanuje\tučitelj\toseba\toseba: Piki Jakob -[stanuje]-> oseba: učitelj\tOsemkrat so mu odkimali in rekli: »Ne, tukaj ni nobenega Pikija Jakoba. Poglejte drugje.« Tako je slednjič prišel v najvišje nadstropje in si oddahnil, ko je za našimi vrati vendarle odkril pravega naslovnika. Piki je bil pisma vesel, zasmilil pa se mu je tisti pismonoša, ki ga je moral tako zelo iskati.Zato je predlagal učitelju, da bi napisal na poštno skrinjico tudi njegovo ime. In tako zdaj piše tam: Tukaj oddajte pošto tudi za Pikija Jakoba, podnajemnika pri učitelju.\nPiki Jakob\toseba\tstanuje\tblok\tprostor\toseba: Piki Jakob -[stanuje]-> prostor: blok\tMoj prijatelj Piki Jakob Kdo je Piki Piki ne stanuje v gozdu, ne v živalskem vrtu, ne v cirkusu, ne v trgovini. Piki stanuje v bloku, v četrtem nadstropju, na polici za igrače. Pikiju je ime Piki, čeprav ni pikast. Tako mu je pač ime. Ni namreč vsakdo belec, ki se Belec piše, in tudi vode ne pije vsakdo, ki se piše Vodopivec. Tako je tudi Pikiju ime Piki. Piki hodi v medvedjo šolo in ima učitelja, ki ni medved, ampak fantek.\nPiki Jakob\toseba\tima učitelja\tfantek\toseba\toseba: Piki Jakob -[ima učitelja]-> oseba: fantek\tMoj prijatelj Piki Jakob Kdo je Piki Piki ne stanuje v gozdu, ne v živalskem vrtu, ne v cirkusu, ne v trgovini. Piki stanuje v bloku, v četrtem nadstropju, na polici za igrače. Pikiju je ime Piki, čeprav ni pikast. Tako mu je pač ime. Ni namreč vsakdo belec, ki se Belec piše, in tudi vode ne pije vsakdo, ki se piše Vodopivec. Tako je tudi Pikiju ime Piki. Piki hodi v medvedjo šolo in ima učitelja, ki ni medved, ampak fantek.\nPiki Jakob\toseba\thodi v šolo\tmedvedja šola\tprostor\toseba: Piki Jakob -[hodi v šolo]-> prostor: medvedja šola\tČe ne veš, kje je Ljubljana, poglej na zemljevid malo na desno in malo navzdol od Pariza. Tukaj hodim v medvedjo šolo in imam mnogo medvedjih prijateljev. Kako je kaj z medvedi v Parizu? Piši mi. Lepo te pozdravlja Piki Jakob« Na drugi list je narisal veliko štirinadstropno hišo. Pred hišo so stali avtomobili, po nebu pa so plavali oblaki. Pismo in sliko je vtaknil v ovojnico, in ko je napisal naslov in prilepil znamko, je učitelj odnesel pošiljko na pošto."}

The procedure GRAPH_RAG_PROMPT_STORY acts as the bridge between the property graph and the LLM (OCI GenAI) to generate rich, narrative-style summaries.

It starts by extracting structured relationships about a selected entity from the SQL_PG_RAG_STORY property graph — not only direct (1-hop) but also indirect (2-hop) connections. These relationships are collected and serialized into a JSON array, forming the contextual foundation (PropertyGraphRag).

Next, the procedure constructs a detailed, instruction-based prompt that guides the LLM to create a coherent, engaging, and well-written story from the extracted facts. The prompt explicitly defines writing style, structure, and tone (in Slovene), ensuring the model produces a natural and informative narrative rather than a simple list of facts.

Once the prompt is assembled, it is sent to the OCI Generative AI model specified in the GRAPHUSER_PROFILE using DBMS_CLOUD_AI.GENERATE. The model’s response — a polished textual summary — is returned in the resp output parameter, along with the JSON of underlying graph facts in PropertyGraphRag.

In essence, this procedure transforms the relational and semantic structure of the property graph into a human-readable story, blending graph analytics with generative AI to produce a meaningful narrative grounded entirely in graph-based data.

The procedure GRAPH_RAG_PROMPT_STORY acts as the bridge between the property graph and the LLM (OCI GenAI) to generate rich, narrative-style summaries.

It starts by extracting structured relationships about a selected entity from the SQL_PG_RAG_STORY property graph — not only direct (1-hop) but also indirect (2-hop) connections. These relationships are collected and serialized into a JSON array, forming the contextual foundation (PropertyGraphRag).

Next, the procedure constructs a detailed, instruction-based prompt that guides the LLM to create a coherent, engaging, and well-written story from the extracted facts. The prompt explicitly defines writing style, structure, and tone (in Slovene), ensuring the model produces a natural and informative narrative rather than a simple list of facts.

Once the prompt is assembled, it is sent to the OCI Generative AI model specified in the GRAPHUSER_PROFILE using DBMS_CLOUD_AI.GENERATE. The model’s response — a polished textual summary — is returned in the resp output parameter, along with the JSON of underlying graph facts in PropertyGraphRag.

In essence, this procedure transforms the relational and semantic structure of the property graph into a human-readable story, blending graph analytics with generative AI to produce a meaningful narrative grounded entirely in graph-based data.

```sql
CREATE OR REPLACE PROCEDURE GRAPH_RAG_PROMPT_STORY (
    debugPrompt      IN  NUMBER   DEFAULT 0,
    entityname       IN  VARCHAR2,
    promptBegin      IN  VARCHAR2,
    resp             OUT CLOB,
    PropertyGraphRag OUT CLOB
) IS
  l_prompt CLOB;
BEGIN
  ---------------------------------------------------------------------------
  -- 1) Build richer JSON context (1-hop + 2-hop) and serialize to CLOB
  ---------------------------------------------------------------------------
    -- Build richer JSON context (1-hop + 2-hop) and serialize to CLOB
-- Build richer JSON context (1-hop + 2-hop) and serialize to CLOB
    SELECT COALESCE(
            JSON_SERIALIZE(
            JSON_ARRAYAGG(
                JSON_OBJECT(
                'hop'       VALUE hop,
                'head'      VALUE head,
                'head_type' VALUE head_type,
                'relation'  VALUE relation,
                'tail'      VALUE tail,
                'tail_type' VALUE tail_type,
                'chunk_id'  VALUE chunk_id,
                'evidence'  VALUE evidence
                RETURNING CLOB)                 -- each object as CLOB
            RETURNING CLOB)                   -- the array as CLOB
            RETURNING CLOB),
            TO_CLOB('[]')
        )
    INTO PropertyGraphRag
    FROM (
    /* -------- 1-hop -------- */
    SELECT *
    FROM (
        SELECT
        1 AS hop,
        CAST(head       AS VARCHAR2(64 CHAR))  AS head,
        CAST(head_type  AS VARCHAR2(64 CHAR))  AS head_type,
        CAST(relation   AS VARCHAR2(128 CHAR))  AS relation,
        CAST(tail       AS VARCHAR2(64 CHAR))  AS tail,
        CAST(tail_type  AS VARCHAR2(64 CHAR))  AS tail_type,
        chunk_id,
        CAST(SUBSTR(evidence, 1, 3990) AS VARCHAR2(3990 CHAR)) AS evidence
        FROM GRAPH_TABLE(
            SQL_PG_RAG_STORY
            MATCH (n IS ENTITY)-[e IS RELATION]->(n2 IS ENTITY)
            COLUMNS (
                n."ENTITY_NAME"  AS head,
                n."ENTITY_TYPE"  AS head_type,
                e."RELATION"     AS relation,
                n2."ENTITY_NAME" AS tail,
                n2."ENTITY_TYPE" AS tail_type,
                e."CHUNK_ID"     AS chunk_id,
                e."CHUNK_DATA"   AS evidence
            )
            )
        WHERE head = entityname
    )
    WHERE ROWNUM <= 100

    UNION ALL

    /* -------- 2-hop -------- */
    SELECT *
    FROM (
        SELECT
        2 AS hop,
        CAST(head       AS VARCHAR2(64 CHAR))  AS head,
        CAST(head_type  AS VARCHAR2(64 CHAR))  AS head_type,
        CAST(relation   AS VARCHAR2(128 CHAR))  AS relation,
        CAST(tail       AS VARCHAR2(64 CHAR))  AS tail,
        CAST(tail_type  AS VARCHAR2(64 CHAR))  AS tail_type,
        chunk_id,
        CAST(SUBSTR(evidence, 1, 3990) AS VARCHAR2(3990 CHAR)) AS evidence
        FROM GRAPH_TABLE(
            SQL_PG_RAG_STORY
            MATCH (n IS ENTITY)-[e1 IS RELATION]->(n2 IS ENTITY)-[e2 IS RELATION]->(n3 IS ENTITY)
            COLUMNS (
                n."ENTITY_NAME"  AS head,
                n."ENTITY_TYPE"  AS head_type,
                e2."RELATION"    AS relation,
                n3."ENTITY_NAME" AS tail,
                n3."ENTITY_TYPE" AS tail_type,
                e2."CHUNK_ID"    AS chunk_id,
                e2."CHUNK_DATA"  AS evidence
            )
            )
        WHERE head = entityname
    )
    WHERE ROWNUM <= 100
    );

   ---------------------------------------------------------------------------
  -- 2) Build a stronger, structured prompt and append JSON context
  ---------------------------------------------------------------------------
  /* l_prompt :=
      TO_CLOB(promptBegin) || CHR(10) ||
      TO_CLOB(
        'Vloga: Si analitik grafa znanja. Uporabi samo podane "facts" kot vir podatkov.' || CHR(10) ||
        CHR(10) ||
        'Navodila:' || CHR(10) ||
        '1) Pripravi podroben in koherenten povzetek za izbrano entiteto.' || CHR(10) ||
        '2) Poudari ključne odnose: kdo–kaj–s kom–zakaj (1- in 2-hop).' || CHR(10) ||
        '3) Združi ponavljanja, razreši navzkrižja: če se dejstva razlikujejo, navedi obe razlagi in označi kot "NEJASNO".' || CHR(10) ||
        '4) Za pomembne trditve dodaj sklice v obliki [id:<chunk_id>] (lahko več id-jev, ločenih z vejicami).' || CHR(10) ||
        '5) Če kaj manjka, to jasno povej; ne uporabiti zunanjega znanja.' || CHR(10) ||
        '6) Jezik: slovenščina. Slog: jedrnat, informativen, brez pretiravanja. Pazi na slovnična pravila in pravilno izgovorjavo.' || CHR(10) ||
        '7) Dolžina: približno 2000 besed.' || CHR(10) ||
        CHR(10) ||
        'Izhodni format (Markdown):' || CHR(10) ||
        '## Povzetek' || CHR(10) ||
        '— več odstavkov z narativnim povzetkom; dodajaj [id:...] za ključne trditve.' || CHR(10) ||
        '## Ključne točke' || CHR(10) ||
        '• Točka 1 [id:...]' || CHR(10) ||
        '• Točka 2 [id:...]' || CHR(10) ||
        '## Nejasnosti ali navzkrižja (če obstajajo)' || CHR(10) ||
        '• Opis nejasnosti in kaj manjka' || CHR(10) ||
        '## Predlogi za nadaljnja vprašanja (neobvezno)' || CHR(10) ||
        '• Vprašanje 1' || CHR(10) ||
        CHR(10) ||
        'Upoštevaj, da "facts" predstavljajo JSON tabelo (array) objektov s polji: hop, head, head_type, relation, tail, tail_type, chunk_id, evidence.' || CHR(10) ||
        'Najprej jih interno preberi/združi, nato pripravi izhod v zgornjem formatu.' || CHR(10) ||
        CHR(10) ||
        'FACTS_JSON_BEGIN' || CHR(10)
      )
      || PropertyGraphRag || CHR(10) ||
      TO_CLOB('FACTS_JSON_END'); */

l_prompt := TO_CLOB(promptBegin) || CHR(10) ||
  '# Tvoja vloga' || CHR(10) ||
  'Si izkušen pripovedovalec zgodb in analitik. Tvoja naloga je iz strukturiranih podatkov ustvariti živo, zanimivo in tekoče berljivo zgodbo o osebi ali entiteti.' || CHR(10) ||
  CHR(10) ||
  '# Temeljni pristop' || CHR(10) ||
  '- Piši kot dober novinar ali biograf - ustvari zgodbo, ne samo seznam dejstev' || CHR(10) ||
  '- Uporabi IZKLJUČNO podane "facts" kot vir - ne domišljaj, ampak povezuj in interpretiraj' || CHR(10) ||
  '- Dejstva vtkaj v narativni tok, ne navajaj jih kot suhe točke' || CHR(10) ||
  '- Jezik: naravna, tekoča slovenščina' || CHR(10) ||
  '- Dolžina: približno 2000 besed' || CHR(10) ||
  CHR(10) ||
  '# Kako pristopiti k pisanju' || CHR(10) ||
  CHR(10) ||
  '## 1. Preberi in vizualiziraj' || CHR(10) ||
  '- Najprej preberi vse podane podatke (JSON struktura: hop, head, head_type, relation, tail, tail_type, chunk_id, evidence)' || CHR(10) ||
  '- Predstavljaj si celostno sliko osebe ali entitete' || CHR(10) ||
  '- Poišči rdečo nit - kaj je osrednja tema ali vloga?' || CHR(10) ||
  '- Identificiraj zanimive povezave, vzorce, razvoj skozi čas' || CHR(10) ||
  CHR(10) ||
  '## 2. Ustvari narativni tok' || CHR(10) ||
  '- Piši v odstavkih, ne v alinejah' || CHR(10) ||
  '- Uporablji prehode med temami: "Poleg tega...", "V tem kontekstu...", "Še posebej zanimivo je..."' || CHR(10) ||
  '- Dejstva povezuj v smiselne celote - če oseba sodeluje z več organizacijami, opiši to kot vzorec, ne kot tri ločena dejstva' || CHR(10) ||
  '- Dodajaj kontekst in pomen: ne samo "X dela v Y", ampak "X je v okviru Y odgovoren za..."' || CHR(10) ||
  CHR(10) ||
  '## 3. Ravnanje z različnimi informacijami' || CHR(10) ||
  '- Če se podatki dopolnjujejo, jih spoji v bogatejši opis' || CHR(10) ||
  '- Če obstajajo razlike ali nejasnosti, jih vključi naravno: "Viri nakazujejo različne vloge - nekateri omenjajo..., drugi poudarjajo..." [id:123,456]' || CHR(10) ||
  '- Ne skrivaj negotovosti, ampak jo predstavi kot del zgodbe' || CHR(10) ||
  CHR(10) ||
  '## 4. Sklicevanje na vire' || CHR(10) ||
  '- Reference [id:...] dodajaj diskretno, naj ne motijo branja' || CHR(10) ||
  '- Postavljaj jih na koncu ključnih trditev ali odstavkov, pred ločili' || CHR(10) ||
  '- Če več virov podpira isto trditev: [id:123,456,789]' || CHR(10) ||
  CHR(10) ||
  '## 5. Pokaži, kaj manjka' || CHR(10) ||
  '- Če bi bil kak podatek koristen za popolnejšo sliko, to omeni v toku pripovedi' || CHR(10) ||
  '- Primer: "Čeprav natančne časovnice ni mogoče določiti iz razpoložljivih podatkov, je jasno da..."' || CHR(10) ||
  CHR(10) ||
  '# Struktura besedila (ne preveč rigidna)' || CHR(10) ||
  CHR(10) ||
  '## Uvodni povzetek (3-4 odstavki)' || CHR(10) ||
  'Začni z zanimivim, celovitim pregledom:' || CHR(10) ||
  '- Kdo je oseba/kaj je entiteta - predstavitev v širšem kontekstu' || CHR(10) ||
  '- Glavne vloge, dejavnosti ali značilnosti' || CHR(10) ||
  '- Zakaj je to zanimivo ali pomembno' || CHR(10) ||
  '- Dodaj reference [id:...] za ključne trditve' || CHR(10) ||
  CHR(10) ||
  '## Glavni del (več odstavkov, 3000-1400 besed)' || CHR(10) ||
  'Razpri zgodbo skozi različne dimenzije:' || CHR(10) ||
  CHR(10) ||
  '**Profesionalno delovanje in vloge**' || CHR(10) ||
  'Opiši, kako oseba deluje v različnih kontekstih. Ne naštevaj funkcij, ampak pripoveduj o delovanju: s kom sodeluje, kaj ustvarja, kako prispeva. [id:...]' || CHR(10) ||
  CHR(10) ||
  '**Mreža odnosov**' || CHR(10) ||
  'Predstavi ključne povezave - ne samo kdo, ampak zakaj so te povezave pomembne. Kako različni odnosi oblikujejo celotno sliko? [id:...]' || CHR(10) ||
  CHR(10) ||
  '**Projekti in dosežki**' || CHR(10) ||
  'Če so znani konkretni projekti ali aktivnosti, jih opiši kot del zgodbe razvoja ali vpliva. [id:...]' || CHR(10) ||
  CHR(10) ||
  '**Razvoj skozi čas (če je relevantno)**' || CHR(10) ||
  'Če podatki to omogočajo, opiši, kako so se vloge ali dejavnosti razvijale. Ali je viden trend, sprememba fokusa, rast odgovornosti? [id:...]' || CHR(10) ||
  CHR(10) ||
  '## Odprti vidiki in nejasnosti (2-3 odstavka)' || CHR(10) ||
  'Če obstajajo neskladja ali manjkajoči podatki, to vključi v narativni obliki:' || CHR(10) ||
  '"Razpoložljivi viri ne dajejo enoznačne slike glede... Medtem ko nekateri poudarjajo [id:123], drugi dokumenti nakazujejo drugačno perspektivo [id:456]. Popolnejša slika bi zahtevala dodatne informacije o..."' || CHR(10) ||
  CHR(10) ||
  '## Zaključek (2-3 odstavka)' || CHR(10) ||
  'Sintetiziraj celotno sliko:' || CHR(10) ||
  '- Kaj je najbolj značilno ali pomembno?' || CHR(10) ||
  '- Kakšen je celostni vtis na podlagi razpoložljivih podatkov?' || CHR(10) ||
  '- Kaj bi bilo smiselno raziskati naprej?' || CHR(10) ||
  CHR(10) ||
  '## Smernice za nadaljnje raziskovanje (3-5 vprašanj)' || CHR(10) ||
  'Na koncu dodaj konkretna vprašanja, ki bi poglobila razumevanje - ne v obliki alinj, ampak kot odstavek z vprašanji, ki naravno izhajajo iz opisanega.' || CHR(10) ||
  CHR(10) ||
  '# Stil in ton' || CHR(10) ||
  '- **Narativno, ne kataložno**: Ustvari tekoče besedilo, ne seznama dejstev' || CHR(10) ||
  '- **Zanimivo, ne suhoparno**: Piši tako, da bi bralca zanimalo brati naprej' || CHR(10) ||
  '- **Analitično, ne spekulativno**: Interpretiraj podatke, a ne dodajaj informacij' || CHR(10) ||
  '- **Naravno, ne akademsko**: Izogibaj se preveč formalnim konstrukcijam' || CHR(10) ||
  '- **Uravnoteženo**: Predstavi celotno sliko, tudi nejasnosti in kompleksnost' || CHR(10) ||
  '- **Slovnično pravilno**: Preveri slovnično pravilnost pripravljenega sestavka in popravi nepravilnosti' || CHR(10) ||
  CHR(10) ||
  'POMEMBNO: Izogibaj se šablonskim formulacijam kot "Pomembno je omeniti...", "Zanimivo je, da..." - raje vključi informacije naravno v tok.' || CHR(10) ||
  CHR(10) ||
  '---' || CHR(10) ||
  CHR(10) ||
  'Spodaj so podatki v JSON formatu. Ustvari iz njih zanimivo, celostno in dobro napisano zgodbo po zgornjih navodilih.' || CHR(10) ||
  CHR(10) ||
  'FACTS_JSON_BEGIN' || CHR(10) ||
  PropertyGraphRag || CHR(10) ||
  'FACTS_JSON_END';

  ---------------------------------------------------------------------------
  -- 3) Ensure AI profile is active
  ---------------------------------------------------------------------------
  DBMS_CLOUD_AI.SET_PROFILE('GRAPHUSER_PROFILE');

  ---------------------------------------------------------------------------
  -- 4) Call LLM and capture response
  ---------------------------------------------------------------------------
  SELECT DBMS_CLOUD_AI.GENERATE(
           prompt       => l_prompt,
           profile_name => 'GRAPHUSER_PROFILE',
           action       => 'chat'
         )
  INTO resp
  FROM dual;

  ---------------------------------------------------------------------------
  -- 5) Optional debug
  ---------------------------------------------------------------------------
  IF debugPrompt = 1 THEN
    DECLARE
      v_len   PLS_INTEGER := DBMS_LOB.getlength(PropertyGraphRag);
      v_pos   PLS_INTEGER := 1;
      v_chunk VARCHAR2(32767);
    BEGIN
      WHILE v_pos <= v_len LOOP
        v_chunk := DBMS_LOB.SUBSTR(PropertyGraphRag, LEAST(32767, v_len - v_pos + 1), v_pos);
        -- DBMS_OUTPUT.PUT_LINE(v_chunk);
        v_pos := v_pos + 32767;
      END LOOP;
    END;
  END IF;

EXCEPTION
  WHEN OTHERS THEN
    RAISE;
END;
/
```

> Procedure GRAPH_RAG_PROMPT_STORY compiled

```sql
DECLARE
  v_resp CLOB;
  v_rag  CLOB;
BEGIN
  ---------------------------------------------------------------------------
  -- Call the GRAPH_RAG_PROMPT_STORY procedure
  -- Adjust entityname and promptBegin to explore different entities.
  ---------------------------------------------------------------------------
  GRAPH_RAG_PROMPT_STORY(
    debugPrompt       => 1,  -- set to 1 to show internal debug info (optional)

    -- Examples - uncomment 'entityname' and 'promptBegin':
    /* entityname       => 'Piki Jakob',
    promptBegin      => 'Podrobno opiši Piki Jakoba.', */
    entityname       => 'učitelj',
    promptBegin      => 'Pojasni, zakaj je Piki njegova najljubša igrača.',
    /* entityname       => 'mama',
    promptBegin      => 'Opiši njen odnos s Pikijem in z učiteljem.', */
    /* entityname         => 'Piki Jakob',
    promptBegin        => 'Podrobno predstavi Piki Jakoba – kaj rad počne, kdo so njegovi prijatelji, in katere jedi ima najraje.', */
    /* entityname       => 'Piki Jakob',
    promptBegin      => 'opiši njegov odnos z učiteljem', */
    
    resp               => v_resp,
    PropertyGraphRag   => v_rag
  );

  ---------------------------------------------------------------------------
  -- Print the results
  ---------------------------------------------------------------------------
  DBMS_OUTPUT.PUT_LINE('=== LLM Response ===');
  DBMS_OUTPUT.PUT_LINE(SUBSTR(v_resp, 1, 32767));

  /* DBMS_OUTPUT.PUT_LINE(CHR(10) || '=== Graph Context (RAG Facts) ===');
  DBMS_OUTPUT.PUT_LINE(SUBSTR(v_rag, 1, 32767)); */

END;
```

> === LLM Response ===
> Piki je zanimiva oseba, ki jo spremljamo skozi različne dogodke in pustolovščine. Njegova zgodba je tesno povezana z učiteljem, ki ga spremlja in mu pomaga pri različnih aktivnostih. Učitelj je Pikijev varuh in ga vzgaja kot lastnega otroka.
> 
> Piki je medvedek, ki živi v Ljubljani in hodi v medvedjo šolo. Ima mnogo medvedjih prijateljev in se zelo rad igra z njimi. Učitelj ga spremlja na različne izlete, kot na primer v živalski vrt, kjer se Piki zelo radzi za opice in druge živali.
> 
> Učitelj in Piki imata zelo blag odnos. Učitelj ga uči različnim stvarem, kot na primer šahu, in ga spodbuja, da se uči in raste. Piki pa učitelja zelo spoštuje in ga posluša. Med njima obstaja močan vez, ki je temelj njihovega odnosa.
> 
> Piki je tudi zelo radoveden in se zelo rad sprašuje o svetu okoli sebe. Učitelj mu pomaga, da razume različne pojme in koncepte, in ga spodbuja, da se sprašuje in išče odgovore.
> 
> V enem od dogodkov se Piki in učitelj odločita, da gremo v živalski vrt. Piki se zelo radzi za opice in druge živali, in učitelj ga spremlja, da se zagotovi, da je varen. Medtem ko so v živalskem vrtu, Piki začne spraševati učitelja o različnih živalih in njihovem življenju.
> 
> Učitelj in Piki imata tudi zelo zabaven odnos. Učitelj ga zelo rad smeši in ga spodbuja, da se smeji tudi on. Piki pa učitelja zelo rad preseneti z različnimi šalami in triki.
> 
> V zaključku lahko rečemo, da je Piki zanimiva oseba, ki jo spremljamo skozi različne dogodke in pustolovščine. Njegova zgodba je tesno povezana z učiteljem, ki ga spremlja in mu pomaga pri različnih aktivnostih. Učitelj in Piki imata zelo blag odnos, ki je temelj njihovega odnosa. Piki je zelo radoveden in se zelo rad sprašuje o svetu okoli sebe, in učitelj ga spodbuja, da se sprašuje in išče odgovore.
> 
> Piki je zelo rad igralec, ki se zelo rad igra z različnimi predmeti in se zelo rad uči novim stvarem. Učitelj ga spodbuja, da se uči in raste, in ga pomaga, da razume različne pojme in koncepte. Piki je tudi zelo radoveden in se zelo rad sprašuje o svetu okoli sebe, in učitelj ga spodbuja, da se sprašuje in išče odgovore.
> 
> V nadaljevanju bi bilo zanimivo izvedeti več o Pikijevih prijateljih in njegovem življenju v medvedji šoli. Kako se Piki uči in raste? Kako se njegovi prijatelji spreminjajo in kakšne so njihove zgodbe? Kako učitelj pomaga Pikiu, da se uči in raste? Te in številne druge vprašanje bi lahko bile odgovorjene v nadaljevanju Pikijeve zgodbe.
> 
> PL/SQL procedure successfully completed.
