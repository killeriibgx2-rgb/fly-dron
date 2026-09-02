package com.zzynes.flydrone;

import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

public class ModNetwork {
    private static final String PROTOCOL_VERSION = "1";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(FlyDroneMod.MOD_ID, "main"),
            () -> PROTOCOL_VERSION,
            PROTOCOL_VERSION::equals,
            PROTOCOL_VERSION::equals
    );

    private static int packetId = 0;

    public static void register() {
        CHANNEL.messageBuilder(DroneControlPacket.class, packetId++, NetworkDirection.PLAY_TO_SERVER)
                .encoder(DroneControlPacket::encode)
                .decoder(DroneControlPacket::decode)
                .consumerMainThread(DroneControlPacket::handle)
                .add();

        CHANNEL.messageBuilder(DroneDisconnectPacket.class, packetId++, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(DroneDisconnectPacket::encode)
                .decoder(DroneDisconnectPacket::decode)
                .consumerMainThread(DroneDisconnectPacket::handle)
                .add();
    }
}