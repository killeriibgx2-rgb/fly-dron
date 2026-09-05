package com.zzynes.flydrone.DRONE;

import com.zzynes.flydrone.DRONE.init.ModBlocks;
import com.zzynes.flydrone.DRONE.init.ModCreativeTabs;
import com.zzynes.flydrone.DRONE.init.ModEntityTypes;
import com.zzynes.flydrone.DRONE.init.ModItems;
import com.zzynes.flydrone.Radio.RadioMod;
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
        RadioMod.init(modEventBus);

        modEventBus.addListener(this::commonSetup);

        MinecraftForge.EVENT_BUS.register(this);
    }

    private void commonSetup(final FMLCommonSetupEvent event) {
        ModNetwork.register();
    }
}