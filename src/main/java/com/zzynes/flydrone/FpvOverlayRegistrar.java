package com.zzynes.flydrone;

import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.RenderGuiEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = FlyDroneMod.MOD_ID, value = Dist.CLIENT)
public class FpvOverlayRegistrar {

    @SubscribeEvent
    public static void onRenderGuiPost(RenderGuiEvent.Post event) {
        FpvOverlay.render(event.getGuiGraphics());
    }
}