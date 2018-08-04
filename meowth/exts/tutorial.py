import asyncio

import discord
from discord.ext import commands


from meowth import utils
from meowth import checks

class Tutorial:
    def __init__(self, bot):
        self.bot = bot

    async def wait_for_cmd(self, tutorial_channel, newbie, command_name):

        # build check relevant to command
        def check(c):
            if not c.channel == tutorial_channel:
                return False
            if not c.author == newbie:
                return False
            if c.command.name == command_name:
                return True
            return False

        # wait for the command to complete
        cmd_ctx = await self.bot.wait_for(
            'command_completion', check=check, timeout=300)

        return cmd_ctx

    def get_overwrites(self, guild, member):
        return {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=False),
            member: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_channels=True),
            guild.me: discord.PermissionOverwrite(
                read_messages=True)
            }

    async def want_tutorial(self, ctx, config):
        report_channels = config['want']['report_channels']
        report_channels.append(ctx.tutorial_channel.id)

        await ctx.tutorial_channel.send(
            f"Questo server usa il comando **{ctx.prefix}want** per permettere "
            "ai membri di ricevere notifiche push sui Pokémon che vogliono! "
            "Io creo dei riuoli per ciascun Pokémon che le persone vogliono, "
            "e @menzionare questi ruoli invierà una notifica a chi "
            f"ne ha fatto richiesta con **{ctx.prefix}want**!\n"
            f"Prova il comando {ctx.prefix}want!\n"
            f"Esempio: `{ctx.prefix}want unown`")

        try:
            await self.wait_for_cmd(ctx.tutorial_channel, ctx.author, 'want')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Ben fatto!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"Ci hai messo troppo a inviare il comando **{ctx.prefix}want**! "
                "Questo canale verrà eliminato in dieci secondi.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()

            return False

        # clean up by removing tutorial from report channel config
        finally:
            report_channels.remove(ctx.tutorial_channel.id)

        return True

    async def wild_tutorial(self, ctx, config):
        report_channels = config['wild']['report_channels']
        report_channels[ctx.tutorial_channel.id] = 'test'

        await ctx.tutorial_channel.send(
            f"Questo server usa il comando **{ctx.prefix}wild** per  "
            "segnalare spawn di selvatici! Quando lo usi, invierò un messaggio "
            "che riassume la segnalazione e contiene un link google maps al luogo "
            "indicato. Se il Pokémon segnalato ha un ruolo associato nel server, "
            "@menzionerò quel ruolo nel mio messaggio! "
            "Una segnalazione deve contenere il nome del Pokémon seguito dalla "
            "sua posizione. "
            "Prova a segnalare un Pokémon selvatico!\n"
            f"Esempio: `{ctx.prefix}wild magikarp qualche parco`")

        try:
            await self.wait_for_cmd(ctx.tutorial_channel, ctx.author, 'wild')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Ben fatto!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"Ci hai messo troppo a inviare il comando **{ctx.prefix}wild**! "
                "Questo canale verrà eliminato in dieci secondi.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        # clean up by removing tutorial from report channel config
        finally:
            del report_channels[ctx.tutorial_channel.id]

        return True

    async def raid_tutorial(self, ctx, config):
        report_channels = config['raid']['report_channels']
        category_dict = config['raid']['category_dict']
        tutorial_channel = ctx.tutorial_channel
        prefix = ctx.prefix
        raid_channel = None

        # add tutorial channel to valid want report channels
        report_channels[tutorial_channel.id] = 'test'

        if config['raid']['categories'] == "region":
            category_dict[tutorial_channel.id] = tutorial_channel.category_id

        async def timeout_raid(cmd):
            await tutorial_channel.send(
                f"Ci hai messo troppo a inviare il comando **{prefix}{cmd}**! "
                "Questo canale verrà eliminato in dieci secondi.")
            await asyncio.sleep(10)
            await tutorial_channel.delete()
            del report_channels[tutorial_channel.id]
            del category_dict[tutorial_channel.id]
            if raid_channel:
                await raid_channel.delete()
                ctx.bot.loop.create_task(self.bot.expire_channel(raid_channel))
            return

        await tutorial_channel.send(
            f"Questo server usa il comando **{prefix}raid** per segnalare "
            "raid! Quando lo usi, invierò un messaggio "
            "che riassume la segnalazione e creerò un canale testuale "
            "per coordinarsi. \n"
            "La segnalazione deve contenere, nell'ordine: il Pokémon (se si tratta "
            "di un raid in corso) o il livello del raid (se è ancora un uovo), "
            "seguito dal nome della palestra in questione;\n"
            "alcuni campi opzionali sono il meteo (usa "
            f"**{prefix}help weather** per vedere quali opzioni sono accettate) e i "
            "minuti rimanenti alla schiusa o al termine (consigliato).\n\n"
            "Prova a segnalare un raid!\n"
            f"Esempio: `{prefix}raid magikarp chiesa locale nuvoloso 42`\n"
            f"`{prefix}raid 3 chiesa locale soleggiato 27`")

        try:
            while True:
                raid_ctx = await self.wait_for_cmd(
                    tutorial_channel, ctx.author, 'raid')

                # get the generated raid channel
                raid_channel = raid_ctx.raid_channel

                if raid_channel:
                    break

                # acknowledge failure and redo wait_for
                await tutorial_channel.send(
                    "Non sembra che abbia funzionato. Assicurati di aver messo tutti i parametri "
                    "nel messaggio e prova di nuovo.")

            # acknowledge and redirect to new raid channel
            await tutorial_channel.send(
                "Ben fatto! Spostiamoci nel nuovo canale raid che hai appena "
                f"creato: {raid_channel.mention}")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('raid')
            return False

        # post raid help info prefix, avatar, user
        helpembed = await utils.get_raid_help(
            ctx.prefix, ctx.bot.user.avatar_url)

        await raid_channel.send(
            f"Questo è un esempio di canale raid. Ecco la lista dei comandi "
            "che puoi inviare da qui:", embed=helpembed)

        await raid_channel.send(
            f"Prova a mostrarti interessato a questo raid!\n\n"
            f"Esempio: `{prefix}interested 5 3b 1g 1r` significa 5 allenatori: "
            "3 Blu, 1 Giallo, 1 Rosso")

        # wait for interested status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'interested')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('interested')
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(
            f"Ben fatto! Per far prima, puoi anche usare **{prefix}i** "
            f"al posto di **{prefix}interested**.")

        await asyncio.sleep(1)
        await raid_channel.send(
            "Ora prova a far sapere che ti sei avviato verso il luogo del raid!\n\n"
            f"Esempio: `{prefix}coming`")

        # wait for coming status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'coming')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('coming')
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(
            "Ottimo! Facci caso, se hai già indicato la composizione del tuo gruppo "
            "in un comando precedente, non devi più farlo per il raid corrente "
            "a meno che tu non desideri cambiarla. Inoltre, "
            f"**{prefix}c** può essere usato al posto di **{prefix}coming** per far prima.")

        await asyncio.sleep(1)
        await raid_channel.send(
            "Ora fai sapere agli altri che sei arrivato al luogo del raid!\n\n"
            f"Esempio: `{prefix}here`")

        # wait for here status update
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'here')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('here')
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(
            f"Ottimo! Anche in questo caso **{prefix}h** può essere usato al posto di "
            f"**{prefix}here**")

        await asyncio.sleep(1)
        await raid_channel.send(
            "Ora vediamo chi altri si è prenotato per questo raid! "
            f"\n\nEsempio: `{prefix}list`")

        # wait for list command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'list')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('list')
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(
            "Fantastico! Dato che non c'è nessuno per strada, prova a usare il comando "
            f"**{prefix}starting** per segnalare che i presenti (lista 'here') stanno entrando "
            "nella lobby di attesa!")

        # wait for starting command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'starting')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('starting')
            return False

        # acknowledge and continue with pauses between
        await asyncio.sleep(1)
        await raid_channel.send(
            f"Ottimo! Ora sei nella lobby ad attendere che passino i due minuti "
            "prima dell'inizio del raid. In questo lasso di tempo "
            "chiunque può richiedere che i giocatori escano con il comando "
            f"**{prefix}backout**. Se la persona che lo richiede è nella lobby, il backout "
            "è automatico. Se ad inviarlo è stato qualcuno che è arrivato al raid "
            "in seguito, verrà richiesta conferma a un membro nella lobby "
            "Quando il backout è confermato, tutti i membri che erano nella lobby, "
            "torneranno nella lista 'here'.")

        await asyncio.sleep(1)
        await raid_channel.send(
            "Un'altra cosa sui canali raid. Calbot si collega a Pokebattler "
            "per fornirti i counter migliori per ogni boss raid in ogni situazione. "
            "Puoi indicare il meteo nella segnalazione raid, o successivamente "
            "col comando "
            f"**{prefix}weather**. Puoi anche selezionare il set di mosse "
            "usando le reazioni nel messaggio iniziale. Se "
            f"hai un account Pokebattler, puoi usare il comando **{prefix}set "
            "pokebattler <id>** per collegarlo! Dopodiché, il comando "
            f"**{prefix}counters** ti invierà per messaggio diretto i counter migliori "
            "tra i Pokémon a TUA disposizione!")

        await asyncio.sleep(1)
        await raid_channel.send(
            "Per concludere: se devi aggiornare il tempo alla schiusa o alla fine, usa "
            f"**{prefix}timerset <minuti rimanenti>**\n\n"
            "Sentiti libero di giocare per un po' con i comandi qui. "
            f"Quando hai finito, scrivi `{prefix}timerset 0` e il raid terminerà.")

        # wait for timerset command completion
        try:
            await self.wait_for_cmd(
                raid_channel, ctx.author, 'timerset')

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await timeout_raid('timerset')
            return False

        # acknowledge and direct member back to tutorial channel
        await raid_channel.send(
            f"Ottimo! Ora torna a {tutorial_channel.mention} per "
            "continuare il tutorial. Questo canale verrà elimianto tra dieci "
            "secondi.")

        await tutorial_channel.send(
            f"Ehi {ctx.author.mention}, quando avrò finito di ripulire il canale "
            "raid, il tutorial continuerà qui!")

        await asyncio.sleep(10)

        # remove tutorial raid channel
        await raid_channel.delete()
        raid_channel = None
        del report_channels[tutorial_channel.id]

        return True

    async def research_tutorial(self, ctx, config):
        report_channels = config['research']['report_channels']
        report_channels[ctx.tutorial_channel.id] = 'test'

        await ctx.tutorial_channel.send(
            f"This server utilizes the **{ctx.prefix}research** command to "
            "report field research tasks! There are two ways to use this "
            f"command: **{ctx.prefix}research** will start an interactive "
            "session where I will prompt you for the task, location, and "
            "reward of the research task. You can also use "
            f"**{ctx.prefix}research <pokestop>, <task>, <reward>** to "
            "submit the report all at once.\n\n"
            f"Try it out by typing `{ctx.prefix}research`")

        # wait for research command completion
        try:
            await self.wait_for_cmd(
                ctx.tutorial_channel, ctx.author, 'research')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Ben fatto!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"You took too long to use the **{ctx.prefix}research** "
                "command! This channel will be deleted in ten seconds.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        # clean up by removing tutorial from report channel config
        finally:
            del report_channels[ctx.tutorial_channel.id]

        return True

    async def team_tutorial(self, ctx):
        await ctx.tutorial_channel.send(
            f"Questo server usa il comando **{ctx.prefix}team** per "
            "permettere ai membri di indicare a quale squadra di Pokémon Go appartengono! "
            f"Scrivi `{ctx.prefix}team mystic` per esempio, se fai parte della squadra Blu.")

        # wait for team command completion
        try:
            await self.wait_for_cmd(
                ctx.tutorial_channel, ctx.author, 'team')

            # acknowledge and wait a second before continuing
            await ctx.tutorial_channel.send("Ben fatto!")
            await asyncio.sleep(1)

        # if no response for 5 minutes, close tutorial
        except asyncio.TimeoutError:
            await ctx.tutorial_channel.send(
                f"You took too long to use the **{ctx.prefix}team** command! "
                "This channel will be deleted in ten seconds.")
            await asyncio.sleep(10)
            await ctx.tutorial_channel.delete()
            return False

        return True

    @commands.group(invoke_without_command=True)
    async def tutorial(self, ctx):
        """Launches an interactive tutorial session for Meowth.

        Meowth will create a private channel and initiate a
        conversation that walks you through the various commands
        that are enabled on the current server."""

        newbie = ctx.author
        guild = ctx.guild
        prefix = ctx.prefix

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ehilà! Ho creato un canale riservato a te dove potrai "
             " svolgere il tutorial! "
             f"Continua in {ctx.tutorial_channel.mention}"),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']
        enabled = [k for k, v in cfg.items() if v.get('enabled', False)]

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere per comunicare con me in questo server! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:

            # start want tutorial
            if 'want' in enabled:
                completed = await self.want_tutorial(ctx, cfg)
                if not completed:
                    return

            # start wild tutorial
            if 'wild' in enabled:
                completed = await self.wild_tutorial(ctx, cfg)
                if not completed:
                    return

            # start raid
            if 'raid' in enabled:
                completed = await self.raid_tutorial(ctx, cfg)
                if not completed:
                    return

            # start exraid
            if 'exraid' in enabled:
                invitestr = ""

                if 'invite' in enabled:
                    invitestr = (
                        "I canali creati con questo comando sono di sola lettura "
                        f"finché i membri non usano il comando **{prefix}invite**.")

                await ctx.tutorial_channel.send(
                    f"Questo server usa il comando **{prefix}exraid** per "
                    "segnalare raid EX! Quando lo usi, invierò un messaggio "
                    "riassume la segnalazione e creerò un canale testuale "
                    f"per coordinarsi. {invitestr}\n"
                    "La segnalazione deve contenere solo il luogo del raid EX.\n\n"
                    "A causa della natura a lungo termine dei raid EX, non proveremo "
                    " a crearne uno adesso.")

            # start research
            if 'research' in enabled:
                completed = await self.research_tutorial(ctx, cfg)
                if not completed:
                    return

            # start team
            if 'team' in enabled:
                completed = await self.team_tutorial(ctx)
                if not completed:
                    return

            # finish tutorial
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 30 secondi.")
            await asyncio.sleep(30)

        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command()
    @checks.feature_enabled('want')
    async def want(self, ctx):
        """Launches an tutorial session for the want feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the various commands
        that are enabled on the current server."""

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ho creato un canale di tutorial privato per te!"
             f"Continua in {ctx.tutorial_channel.mention}."),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere sul comando want! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:
            await self.want_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 10 secondi.")
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command()
    @checks.feature_enabled('wild')
    async def wild(self, ctx):
        """Launches an tutorial session for the wild feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through wild command."""

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ho creato un canale di tutorial privato per te!"
             f"Continua in {ctx.tutorial_channel.mention}."),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere sul comando wild! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:
            await self.wild_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 10 secondi.")
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command()
    @checks.feature_enabled('raid')
    async def raid(self, ctx):
        """Launches an tutorial session for the raid feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the raid commands."""

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ho creato un canale di tutorial privato per te!"
             f"Continua in {ctx.tutorial_channel.mention}."),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere sul comando raid! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:
            await self.raid_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 10 secondi.")
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command()
    @checks.feature_enabled('research')
    async def research(self, ctx):
        """Launches an tutorial session for the research feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the research command."""

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ho creato un canale di tutorial privato per te!"
             f"Continua in {ctx.tutorial_channel.mention}."),
            delete_after=20.0)

        # get tutorial settings
        cfg = self.bot.guild_dict[guild.id]['configure_dict']

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere sul comando research! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:
            await self.research_tutorial(ctx, cfg)
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 10 secondi.")
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

    @tutorial.command()
    @checks.feature_enabled('team')
    async def team(self, ctx):
        """Launches an tutorial session for the team feature.

        Meowth will create a private channel and initiate a
        conversation that walks you through the team command."""

        newbie = ctx.author
        guild = ctx.guild

        # get channel overwrites
        ows = self.get_overwrites(guild, newbie)

        # create tutorial channel
        name = utils.sanitize_channel_name(newbie.display_name+"-tutorial")
        ctx.tutorial_channel = await guild.create_text_channel(
            name, overwrites=ows)
        await ctx.message.delete()
        await ctx.send(
            ("Ho creato un canale di tutorial privato per te!"
             f"Continua in {ctx.tutorial_channel.mention}."),
            delete_after=20.0)

        await ctx.tutorial_channel.send(
            f"Ciao {ctx.author.mention}! Sono Calbot, un bot di Discord per "
            "le comunità di Pokémon Go! Ho creato questo canale per insegnarti "
            "tutto ciò che devi sapere sul comando team! Sappi "
            "che puoi abbandonare questo tutorial quando vuoi e io eliminerò questo canale "
            "entro 5 minuti. Bene, cominciamo!")

        try:
            await self.team_tutorial(ctx)
            await ctx.tutorial_channel.send(
                f"Questo conclude il tutorial di Calbot! "
                "Questo canale verrà eliminato in 10 secondi.")
            await asyncio.sleep(10)
        finally:
            await ctx.tutorial_channel.delete()

def setup(bot):
    bot.add_cog(Tutorial(bot))
