package com.zzynes.flydrone;

import com.zzynes.flydrone.init.ModBlocks;
import com.zzynes.flydrone.init.ModCreativeTabs;
import com.zzynes.flydrone.init.ModEntityTypes;
import com.zzynes.flydrone.init.ModItems;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.event.lifecycle.FMLCommonSetupEvent;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;

@Mod("fly_drone")
public class FlyDroneMod {
    public static final String MOD_ID = "fly_drone";

    public FlyDroneMod() {
        IEventBus modEventBus = FMLJavaModLoadingContext.get().getModEventBus();

        ModBlocks.register(modEventBus);
        ModItems.register(modEventBus);
        ModCreativeTabs.register(modEventBus);
        ModEntityTypes.register(modEventBus);

        modEventBus.addListener(this::commonSetup);

        MinecraftForge.EVENT_BUS.register(this);
    }

    private void commonSetup(final FMLCommonSetupEvent event) {
        ModNetwork.register();
    }
}