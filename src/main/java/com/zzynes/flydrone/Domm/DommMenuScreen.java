package com.zzynes.flydrone.Domm;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;

public class DommMenuScreen extends AbstractContainerScreen<DommMenu> {
    private static final ResourceLocation GUI_TEXTURE = new ResourceLocation("fly_drone", "textures/gui/container/domm_gui.png");
    private static final ResourceLocation FUEL_TEXTURE = new ResourceLocation("fly_drone", "textures/gui/container/top1.png");

    public DommMenuScreen(DommMenu menu, Inventory playerInventory, Component title) {
        super(menu, playerInventory, title);
        this.imageWidth = 176;
        this.imageHeight = 166;
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTick, int mouseX, int mouseY) {
        int x = (this.width - this.imageWidth) / 2;
        int y = (this.height - this.imageHeight) / 2;
        graphics.blit(GUI_TEXTURE, x, y, 0, 0, this.imageWidth, this.imageHeight, 256, 256);

        int coalStored = this.menu.getCoalStored();
        if (coalStored > 0) {
            float percent = coalStored / 64.0f;
            int barHeight = (int) (48 * percent);
            if (barHeight < 1) barHeight = 1;
            graphics.blit(FUEL_TEXTURE, x + 8, y + 32 + (48 - barHeight), 0, 48 - barHeight, 16, barHeight, 16, 48);
        }

        int temperature = this.menu.getTemperature();
        int gaugeIndex = (int) ((float) temperature / 2000.0f * 17);
        if (gaugeIndex > 16) gaugeIndex = 16;
        if (gaugeIndex < 0) gaugeIndex = 0;
        ResourceLocation pressureTexture = new ResourceLocation("fly_drone", "textures/gui/container/pressure" + (gaugeIndex + 1) + ".png");
        graphics.blit(pressureTexture, x + 50, y + 2, 0, 0, 16, 16, 16, 16);
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        renderBackground(graphics);
        super.render(graphics, mouseX, mouseY, partialTick);
        renderTooltip(graphics, mouseX, mouseY);
    }
}