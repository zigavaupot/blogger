# Graphs – the bridge between data and generative artificial intelligence.

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
> ...

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
> ...

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
> ...

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
> ... 

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
